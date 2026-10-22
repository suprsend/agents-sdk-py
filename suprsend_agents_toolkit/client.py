from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from collections.abc import Callable
from typing import Any, TYPE_CHECKING

import aiohttp

from suprsend_agents_toolkit.auth import SuprSendAuth, JWTAuth

_WORKSPACE_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

if TYPE_CHECKING:
    from suprsend_agents_toolkit.context import ToolContext


class AsyncSuprSendClient:
    """
    Async HTTP client for all SuprSend API surfaces.

    Context is stored on the client at construction time so every tool
    only needs to receive the client — context flows through client.context.

        client = AsyncSuprSendClient(auth=ServiceTokenAuth("sst_..."), context=ctx)
        client.context.workspace   # → "acme"
        client.context.tenant_id   # → "acme-prod"

    Auth swap for JWT (copilot per-request override):

        jwt_client = client._with_jwt("eyJ...")
        # same context, same _workspace_cache, different auth header

    Workspace-level calls go through the SuprSend Python SDK:

        sdk = await client.get_sdk_instance("acme")
        # exchange_workspace_credentials("acme") on first call, cached thereafter
        # sdk.users.get(distinct_id), sdk.objects.get_full_preference(...), etc.
    """

    def __init__(
        self,
        auth: SuprSendAuth | None,
        context: "ToolContext",
        jwt_getter: "Callable[[Any], str] | None" = None,
        policy: dict | None = None,
    ) -> None:
        self.auth = auth
        self.context = context
        self.base_url = context.base_url.rstrip("/")
        self.mgmnt_url = context.mgmnt_url.rstrip("/")
        self.jwt_getter = jwt_getter  # Callable[[config], str] — returns JWT or ""
        # Enforcement policy for tool behaviour annotations.
        # Keys: allow_writes (bool), allow_destructive (bool).
        self.policy: dict = policy or {"allow_writes": True, "allow_destructive": True}
        # workspace slug → (key, secret) — populated by exchange_workspace_credentials
        self._workspace_cache: dict[str, tuple[str, str]] = {}
        # Lock guarding cache writes; shared with _with_jwt() children via _with_jwt()
        self._cache_lock: asyncio.Lock = asyncio.Lock()
        # Persistent session — created lazily, shared with _with_jwt() children
        self._session: aiohttp.ClientSession | None = None

    def _with_jwt(self, jwt_token: str) -> "AsyncSuprSendClient":
        """
        Return a derived client using JWTAuth.
        Shares the same context and _workspace_cache as the parent so an
        exchange already performed is not repeated.
        Each derived client owns its own session so that closing one does
        not affect the parent or any sibling clients.
        """
        new = AsyncSuprSendClient(auth=JWTAuth(jwt_token), context=self.context, jwt_getter=self.jwt_getter, policy=self.policy)
        new._workspace_cache = self._workspace_cache
        new._cache_lock = self._cache_lock
        return new

    async def close(self) -> None:
        """Close the underlying aiohttp session. Call when the client is no longer needed."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "AsyncSuprSendClient":
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    # ── Low-level helpers ─────────────────────────────────────────────────────

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60)
            )
        return self._session

    async def get(self, url: str, params: dict | None = None) -> Any:
        headers = self.auth.get_headers()
        async with self._get_session().get(url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def post(self, url: str, payload: dict | None = None) -> Any:
        body = json.dumps(payload or {}).encode()
        headers = self.auth.get_headers()
        async with self._get_session().post(url, data=body, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    # ── Exchange ──────────────────────────────────────────────────────────────

    def _make_cache_key(self, workspace: str) -> str:
        """
        Build a cache key scoped to both the calling user and workspace slug.

        For JWT auth the token payload contains `user_id` which is unique per
        user/org, so two organisations that happen to share the same workspace
        slug will never collide in the cache.  For ServiceToken auth the token
        is already org-scoped, so the workspace slug alone is sufficient.

        Also validates JWT expiry so an expired token cannot initiate a new
        workspace credential exchange (cached entries from a previous valid
        session remain usable since the workspace key/secret are independent
        of the JWT lifetime).
        """
        if isinstance(self.auth, JWTAuth):
            try:
                payload_b64 = self.auth.token.split(".")[1]
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                claims = json.loads(base64.urlsafe_b64decode(payload_b64))
            except Exception as e:
                raise ValueError(f"Failed to decode JWT payload: {e}") from e
            user_id = claims.get("user_id")
            if not user_id:
                raise ValueError("JWT payload missing user_id — cannot safely scope workspace cache")
            exp = claims.get("exp")
            if exp is not None and time.time() > exp:
                raise ValueError("JWT token has expired — re-authenticate to continue.")
            return f"{user_id}:{workspace}"
        return workspace

    async def exchange_workspace_credentials(
        self, workspace: str
    ) -> tuple[str, str]:
        """
        Exchange the current service/JWT token for workspace key + secret.

        GET {hub_url}/v1/{workspace}/ws_key/bridge
        Returns (workspace_key, workspace_secret).
        Result is cached — only one network call per workspace per lifetime.
        """
        if not workspace or not _WORKSPACE_RE.match(workspace):
            raise ValueError(f"Invalid workspace slug: {workspace!r}")

        cache_key = self._make_cache_key(workspace)
        if cache_key in self._workspace_cache:
            return self._workspace_cache[cache_key]

        async with self._cache_lock:
            # Double-check after acquiring the lock — another coroutine may have
            # populated the cache while we were waiting.
            if cache_key in self._workspace_cache:
                return self._workspace_cache[cache_key]

            url = f"{self.base_url}/v1/{workspace}/ws_key/bridge"
            result = await self.get(url)
            key = result["key"]
            secret = result["secret"]
            self._workspace_cache[cache_key] = (key, secret)
            return key, secret

    async def get_sdk_instance(self, workspace: str):
        """
        Exchange workspace credentials and return a fresh Suprsend SDK instance.

        The exchange result is cached — only one network call per workspace per
        client lifetime.  The Suprsend instance itself is intentionally not
        cached because it is synchronous (requests-based) and must be
        re-created per tool call.
        """
        from suprsend import Suprsend
        key, secret = await self.exchange_workspace_credentials(workspace)
        return Suprsend(key, secret, base_url=self.base_url)

    def get_management_instance(self):
        """
        Return a SuprsendManagement instance with no auth preset.

        Auth headers are injected per-call by ManagementTool._mgmnt_headers()
        so the same instance can serve different auth contexts if needed.
        """
        from suprsend_management import SuprsendManagement
        return SuprsendManagement(base_url=self.mgmnt_url)


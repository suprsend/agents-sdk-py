from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TYPE_CHECKING

import aiohttp

from suprsend_agents.auth import SuprSendAuth, JWTAuth

if TYPE_CHECKING:
    from suprsend_agents.context import ToolContext


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
        jwt_getter: Callable[[], str] | None = None,
    ) -> None:
        self.auth = auth
        self.context = context
        self.base_url = context.base_url.rstrip("/")
        self.mgmnt_url = context.mgmnt_url.rstrip("/")
        self.jwt_getter = jwt_getter
        # workspace slug → (key, secret) — populated by exchange_workspace_credentials
        self._workspace_cache: dict[str, tuple[str, str]] = {}
        # Persistent session — created lazily, shared with _with_jwt() children
        self._session: aiohttp.ClientSession | None = None

    def _with_jwt(self, jwt_token: str) -> "AsyncSuprSendClient":
        """
        Return a derived client using JWTAuth.
        Shares the same context and _workspace_cache as the parent so an
        exchange already performed is not repeated.
        """
        new = AsyncSuprSendClient(auth=JWTAuth(jwt_token), context=self.context, jwt_getter=self.jwt_getter)
        new._workspace_cache = self._workspace_cache
        new._session = self._session  # share the connection pool
        return new

    # ── Low-level helpers ─────────────────────────────────────────────────────

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
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

    async def exchange_workspace_credentials(
        self, workspace: str
    ) -> tuple[str, str]:
        """
        Exchange the current service/JWT token for workspace key + secret.

        GET {hub_url}/v1/{workspace}/ws_key/bridge
        Returns (workspace_key, workspace_secret).
        Result is cached — only one network call per workspace per lifetime.
        """
        if workspace in self._workspace_cache:
            return self._workspace_cache[workspace]

        url = f"{self.base_url}/v1/{workspace}/ws_key/bridge"
        result = await self.get(url)
        key = result["key"]
        secret = result["secret"]
        self._workspace_cache[workspace] = (key, secret)
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

    # ── Management API (service token / JWT) ──────────────────────────────────

    async def mgmnt_get(self, path: str, params: dict | None = None) -> Any:
        """GET against the management API (service token / JWT auth)."""
        url = f"{self.mgmnt_url}/{path.lstrip('/')}"
        return await self.get(url, params=params)

    async def mgmnt_post(self, path: str, payload: dict) -> Any:
        """POST against the management API (service token / JWT auth)."""
        url = f"{self.mgmnt_url}/{path.lstrip('/')}"
        return await self.post(url, payload)

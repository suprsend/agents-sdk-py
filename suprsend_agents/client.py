from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, TYPE_CHECKING

import aiohttp

from suprsend_agents.auth import SuprSendAuth, JWTAuth

if TYPE_CHECKING:
    from suprsend_agents.context import ToolContext


def _hmac_headers(
    workspace_key: str,
    workspace_secret: str,
    method: str,
    path: str,
    body: bytes,
) -> dict[str, str]:
    """
    Internal HMAC-SHA256 signing for workspace-level hub API calls.
    Not part of the public auth surface — callers always start with
    ServiceTokenAuth or JWTAuth; the client handles signing transparently.
    """
    date = format_datetime(datetime.now(timezone.utc), usegmt=True)
    content_md5 = base64.b64encode(hashlib.md5(body).digest()).decode()
    string_to_sign = (
        f"{method.upper()}\n{content_md5}\napplication/json\n{date}\n{path}"
    )
    signature = base64.b64encode(
        hmac.new(
            workspace_secret.encode(),
            string_to_sign.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()
    return {
        "Authorization": f"{workspace_key}:{signature}",
        "Date": date,
        "Content-MD5": content_md5,
        "Content-Type": "application/json",
    }


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

    Workspace-level hub calls auto-exchange on first use:

        await client.workspace_post("acme", "acme/trigger/", payload)
        # 1. exchange_workspace_credentials("acme") if not cached
        # 2. HMAC-sign the request with the returned key+secret
    """

    def __init__(self, auth: SuprSendAuth, context: "ToolContext") -> None:
        self.auth = auth
        self.context = context
        self.base_url = context.base_url.rstrip("/")
        self.mgmnt_url = context.mgmnt_url.rstrip("/")
        # workspace slug → (key, secret) — populated by exchange_workspace_credentials
        self._workspace_cache: dict[str, tuple[str, str]] = {}

    def _with_jwt(self, jwt_token: str) -> "AsyncSuprSendClient":
        """
        Return a derived client using JWTAuth.
        Shares the same context and _workspace_cache as the parent so an
        exchange already performed is not repeated.
        """
        new = AsyncSuprSendClient(
            auth=JWTAuth(jwt_token),
            context=self.context,
        )
        new._workspace_cache = self._workspace_cache
        return new

    # ── Low-level helpers ─────────────────────────────────────────────────────

    async def get(self, url: str, params: dict | None = None) -> Any:
        headers = self.auth.get_headers()
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def post(self, url: str, payload: dict | None = None) -> Any:
        body = json.dumps(payload or {}).encode()
        headers = self.auth.get_headers()
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=body, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()

    # ── Exchange ──────────────────────────────────────────────────────────────

    async def exchange_workspace_credentials(
        self, workspace: str
    ) -> tuple[str, str]:
        """
        Exchange the current service/JWT token for workspace key + secret.

        GET {base_url}/v1/{workspace}/ws_key/bridge
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

    # ── Workspace-level hub API (HMAC-signed) ─────────────────────────────────

    async def workspace_get(
        self,
        workspace: str,
        path: str,
        params: dict | None = None,
    ) -> Any:
        """GET against the hub API, HMAC-signed with workspace credentials."""
        key, secret = await self.exchange_workspace_credentials(workspace)
        full_path = f"/{path.lstrip('/')}"
        headers = _hmac_headers(key, secret, "GET", full_path, b"")
        url = f"{self.base_url}{full_path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def workspace_post(
        self,
        workspace: str,
        path: str,
        payload: dict,
    ) -> Any:
        """POST against the hub API, HMAC-signed with workspace credentials."""
        key, secret = await self.exchange_workspace_credentials(workspace)
        full_path = f"/{path.lstrip('/')}"
        body = json.dumps(payload).encode()
        headers = _hmac_headers(key, secret, "POST", full_path, body)
        url = f"{self.base_url}{full_path}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=body, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()

    # ── Management API (service token / JWT) ──────────────────────────────────

    async def mgmnt_get(self, path: str, params: dict | None = None) -> Any:
        """GET against the management API (service token / JWT auth)."""
        url = f"{self.mgmnt_url}/{path.lstrip('/')}"
        return await self.get(url, params=params)

    async def mgmnt_post(self, path: str, payload: dict) -> Any:
        """POST against the management API (service token / JWT auth)."""
        url = f"{self.mgmnt_url}/{path.lstrip('/')}"
        return await self.post(url, payload)

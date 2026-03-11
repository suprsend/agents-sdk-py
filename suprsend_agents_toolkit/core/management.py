from __future__ import annotations

import asyncio
from typing import Any, Callable

from suprsend_agents_toolkit.auth import JWTAuth
from suprsend_agents_toolkit.core.base import SuprSendTool


class ManagementTool(SuprSendTool):
    """
    Base class for all management API tools.

    Differences from SuprSendTool (hub tools):
    - No workspace credential exchange — management API uses direct auth.
    - ServiceTokenAuth  → Authorization: ServiceToken <token>
    - JWTAuth           → Authorization: Bearer <jwt>
                          x-ss-api-secret: <secret>  (from context.api_secret)
    - Calls are dispatched through SuprsendManagement SDK (synchronous, requests-based)
      via asyncio.to_thread, same pattern as hub tools using suprsend-py-sdk.

    Subclasses define:
        permission_category    = "management"   (inherited)
        permission_subcategory = "<resource>"   e.g. "workflows", "tenants"
        permission_operation   = "read" | "manage"

    And implement:
        execute(client, **kwargs) → str

    Typical execute() pattern:

        async def execute(self, client, **kwargs):
            return await self._mgmnt_run(
                client,
                lambda mgmt, **kw: mgmt.workspaces.list(**kw),
                **kwargs,
            )
    """

    permission_category: str | None = "management"
    permission_subcategory: str | None = None  # e.g. "workflows", "tenants"
    permission_operation: str | None = None    # "read" | "manage"

    def _mgmnt_headers(self, client: Any) -> dict:
        """
        Build the auth headers for a management API call.

        ServiceTokenAuth:  Authorization: ServiceToken <token>
        JWTAuth:           Authorization: Bearer <jwt>
                           x-ss-api-secret: <secret>  (if context.api_secret set)
        """
        headers = client.auth.get_headers()
        if isinstance(client.auth, JWTAuth) and client.context.api_secret:
            headers["x-ss-api-secret"] = client.context.api_secret
        return headers

    async def _mgmnt_run(
        self,
        client: Any,
        fn: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a synchronous management SDK call in a thread pool.

        Builds a SuprsendManagement instance (no auth at init), then injects
        auth headers via extra_headers so the right credentials are sent for
        the current ServiceToken or JWT context.

        Args:
            client:   AsyncSuprSendClient resolved for this tool invocation.
            fn:       Callable(mgmt, *args, extra_headers=..., **kwargs).
                      Typically a lambda wrapping a mgmt.<resource>.<method> call.
            *args:    Positional args forwarded to fn after mgmt.
            **kwargs: Keyword args forwarded to fn (extra_headers must NOT be
                      in kwargs — it is always injected here).
        """
        mgmt = client.get_management_instance()
        extra = self._mgmnt_headers(client)
        return await asyncio.to_thread(fn, mgmt, *args, extra_headers=extra, **kwargs)

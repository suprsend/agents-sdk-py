from __future__ import annotations

import asyncio
from typing import Any

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
      via asyncio.to_thread.

    Subclasses define:
        permission_category    = "management"   (inherited)
        permission_subcategory = "<resource>"   e.g. "workflows", "tenants"
        permission_operation   = "read" | "manage"

    And implement:
        execute(client, **kwargs) → str

    Typical execute() pattern:

        async def execute(self, client, **kwargs):
            ws = self._workspace(client, kwargs)
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.workflows.list, ws, extra_headers=headers
            )
            return yaml.dump(result, default_flow_style=False)
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

    def _mgmnt(self, client: Any) -> tuple:
        """
        Return (mgmt_instance, auth_headers) ready for asyncio.to_thread calls.

        Usage in execute():
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.workflows.get, workspace, slug, extra_headers=headers
            )
        """
        return client.get_management_instance(), self._mgmnt_headers(client)

    # _api_error is inherited from SuprSendTool.

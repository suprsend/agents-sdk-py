import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool


# ── GetTenantTool ─────────────────────────────────────────────────────────────

class GetTenantInput(BaseModel):
    tenant_id: str = Field(
        description="Unique identifier of the tenant to fetch."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetTenantTool(SuprSendTool):
    """GET {base_url}/v1/tenant/{tenant_id}/"""

    name = "get_tenant"
    description = (
        "Fetches the full configuration for a tenant — branding (logo, colors), preference page "
        "URLs, blocked channels, social links, and custom properties. Use this to inspect tenant "
        "setup or verify branding before triggering tenant-scoped notifications."
    )
    args_schema = GetTenantInput
    permission_category = "tenants"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        tenant_id: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not tenant_id:
            return "Error: tenant_id is required."

        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.tenants.get, tenant_id)
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"fetching tenant '{tenant_id}'")


# ── GetTenantPreferenceTool ───────────────────────────────────────────────────

class GetTenantPreferenceInput(BaseModel):
    tenant_id: str = Field(
        description="Unique identifier of the tenant to fetch default preferences for."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )
    limit: int = Field(
        default=20,
        description="Number of categories to return (max 1000).",
    )
    offset: int = Field(
        default=0,
        description="Offset for pagination.",
    )
    tags: str = Field(
        default="",
        description="Filter categories by tag.",
    )


class GetTenantPreferenceTool(SuprSendTool):
    """GET {base_url}/v1/tenant/{tenant_id}/category/"""

    name = "get_tenant_preference"
    description = (
        "Fetches the default notification preference settings for all categories under a tenant. "
        "Each category shows workspace-level defaults (default_preference, default_mandatory_channels, "
        "default_opt_in_channels) and tenant-level overrides (preference, mandatory_channels, "
        "opt_in_channels, blocked_channels). Use this to understand what preference rules apply "
        "to users under a specific tenant by default. Supports pagination and tag-based filtering."
    )
    args_schema = GetTenantPreferenceInput
    permission_category = "tenants"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        tenant_id: str = "",
        limit: int = 20,
        offset: int = 0,
        tags: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not tenant_id:
            return "Error: tenant_id is required."

        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(
                sdk.tenants.get_all_categories_preference, tenant_id, limit, offset, tags
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"fetching preferences for tenant '{tenant_id}'")

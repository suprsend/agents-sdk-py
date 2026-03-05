import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool


# ── GetTenantTool ─────────────────────────────────────────────────────────────

class GetTenantInput(BaseModel):
    tenant_id: str = Field(
        description="The unique identifier of the tenant."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetTenantTool(SuprSendTool):
    """
    GET {base_url}/v1/tenant/{tenant_id}/

    Returns the full tenant profile: name, logo, timezone, blocked_channels,
    preference URLs, brand colors, social links, and custom properties.
    """

    name = "get_tenant"
    description = (
        "Get details for a tenant in SuprSend. "
        "Returns the tenant's name, branding, blocked channels, "
        "preference page URLs, and custom properties."
    )
    args_schema = GetTenantInput
    permission_category = "tenants"
    permission_operation = "read"

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
            return f"Error fetching tenant '{tenant_id}': {e}"


# ── GetTenantPreferenceTool ───────────────────────────────────────────────────

class GetTenantPreferenceInput(BaseModel):
    tenant_id: str = Field(
        description="The unique identifier of the tenant."
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
    """
    GET {base_url}/v1/tenant/{tenant_id}/category/

    Returns all notification category preferences for a tenant, including
    per-category settings like preference, visible_to_subscriber,
    mandatory_channels, and blocked_channels.
    """

    name = "get_tenant_preference"
    description = (
        "Get all notification category preferences for a tenant in SuprSend. "
        "Returns per-category settings: preference, visibility, mandatory channels, "
        "and blocked channels. Supports pagination and tag-based filtering."
    )
    args_schema = GetTenantPreferenceInput
    permission_category = "tenants"
    permission_operation = "read"

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
            return f"Error fetching preferences for tenant '{tenant_id}': {e}"
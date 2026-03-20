import asyncio
import yaml

import json

from pydantic import BaseModel, Field, field_validator

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


# ── UpsertTenantTool ──────────────────────────────────────────────────────────

class UpsertTenantInput(BaseModel):
    tenant_id: str = Field(
        description="Unique identifier of the tenant to create or update."
    )
    payload: dict = Field(
        description=(
            "Tenant configuration fields. "
            "Required: tenant_name (string) — the organization display name. "
            "Optional: logo (URL string), primary_color (hex), secondary_color (hex), tertiary_color (hex), "
            "timezone (IANA timezone string — fallback timezone for recipients), "
            "blocked_channels (list of channel names to skip, e.g. [\"email\", \"sms\"]), "
            "embedded_preference_url (string — in-product notification center link), "
            "social_links (dict — supported keys: website, facebook, linkedin, x, instagram, medium, discord, telegram, youtube, tiktok; use empty string to remove a link), "
            "properties (dict of custom key-value pairs, accessible in templates as {{$brand.prop}})."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )

    @field_validator("payload", mode="before")
    @classmethod
    def parse_payload(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class UpsertTenantTool(SuprSendTool):
    """POST {base_url}/v1/tenant/{tenant_id}/"""

    name = "upsert_tenant"
    description = (
        "Create or update a tenant. A tenant represents a customer organization and controls "
        "branding (logo, colors), preference page URLs, blocked channels, social links, and "
        "custom properties. If the tenant already exists it is updated with the provided fields."
    )
    args_schema = UpsertTenantInput
    permission_category = "tenants"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        tenant_id: str = "",
        payload: dict = {},
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not tenant_id:
            return "Error: tenant_id is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.tenants.upsert, tenant_id, payload)
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"upserting tenant '{tenant_id}'")

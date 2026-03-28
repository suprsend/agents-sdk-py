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
            return yaml.dump(result, default_flow_style=False), result
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
            return yaml.dump(result, default_flow_style=False), result
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
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"upserting tenant '{tenant_id}'")


# ── UpdateTenantPreferenceCategoryTool ────────────────────────────────────────

_VALID_CHANNELS_TENANT = ["email", "sms", "whatsapp", "androidpush", "iospush", "webpush", "inbox", "slack", "ms_teams"]
_CHANNELS_DESC_TENANT = ", ".join(f'"{c}"' for c in _VALID_CHANNELS_TENANT)


class UpdateTenantPreferenceCategoryInput(BaseModel):
    tenant_id: str = Field(description="Unique identifier of the tenant.")
    category: str = Field(description="Preference category slug to update.")
    preference: str = Field(
        default="",
        description='Category default preference for users in this tenant. One of "opt_in", "opt_out", or "cant_unsubscribe".',
    )
    enabled_for_tenant: bool = Field(
        default=None,
        description="Whether this category is active for the tenant. True to enable, False to disable.",
    )
    visible_to_subscriber: bool = Field(
        default=None,
        description="Whether users can see and change this category preference. True to show, False to hide.",
    )
    mandatory_channels: list = Field(
        default_factory=list,
        description=(
            f"Channels subscribers cannot opt out of. Valid: {_CHANNELS_DESC_TENANT}. "
            "ONLY provide when specific channels are named. Omit for all channels or when not applicable."
        ),
    )
    opt_in_channels: list = Field(
        default_factory=list,
        description=(
            f"Channels opted in by default for this category. Valid: {_CHANNELS_DESC_TENANT}. "
            "ONLY provide when the user names particular channels. "
            "Omit entirely if applying to all channels — omitting means all channels."
        ),
    )
    blocked_channels: list = Field(
        default_factory=list,
        description=(
            f"Channels completely blocked for this category. Valid: {_CHANNELS_DESC_TENANT}. "
            "ONLY provide when specific channels are named. Omit for all channels or when not applicable."
        ),
    )
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("mandatory_channels", "opt_in_channels", "blocked_channels", mode="before")
    @classmethod
    def parse_channel_lists(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class UpdateTenantPreferenceCategoryTool(SuprSendTool):
    """PATCH {base_url}/v1/tenant/{tenant_id}/preference/category/{category}/"""

    name = "update_tenant_preference_category"
    description = (
        "Update a tenant's default notification preference for a specific category. "
        "Controls whether the category is visible to subscribers, what the default opt-in/out is, "
        "which channels are mandatory, opted-in, or blocked for users under this tenant."
    )
    args_schema = UpdateTenantPreferenceCategoryInput
    permission_category = "tenants"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        tenant_id: str = "",
        category: str = "",
        preference: str = "",
        enabled_for_tenant=None,
        visible_to_subscriber=None,
        mandatory_channels: list = [],
        opt_in_channels: list = [],
        blocked_channels: list = [],
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not tenant_id:
            return "Error: tenant_id is required."
        if not category:
            return "Error: category is required."
        payload: dict = {}
        if preference:
            if preference not in ("opt_in", "opt_out", "cant_unsubscribe"):
                return "Error: preference must be 'opt_in', 'opt_out', or 'cant_unsubscribe'."
            payload["preference"] = preference
        if enabled_for_tenant is not None:
            payload["enabled_for_tenant"] = enabled_for_tenant
        if visible_to_subscriber is not None:
            payload["visible_to_subscriber"] = visible_to_subscriber
        if mandatory_channels:
            payload["mandatory_channels"] = mandatory_channels
        if opt_in_channels:
            payload["opt_in_channels"] = opt_in_channels
        if blocked_channels:
            payload["blocked_channels"] = blocked_channels
        if not payload:
            return "Error: at least one field must be provided to update."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(
                sdk.tenants.update_category_preference, tenant_id, category, payload
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"updating category preference for tenant '{tenant_id}'")

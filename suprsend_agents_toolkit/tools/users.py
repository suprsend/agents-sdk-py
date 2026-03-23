import asyncio

import yaml

import json

from pydantic import BaseModel, Field, field_validator

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool


# ── GetUserTool ───────────────────────────────────────────────────────────────

class GetUserInput(BaseModel):
    distinct_id: str = Field(
        description="Unique identifier of the user in your system."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetUserTool(SuprSendTool):
    """GET {base_url}/v1/user/{distinct_id}/"""

    name = "get_user"
    description = (
        "Fetch a user's complete profile by their distinct_id — including all channel addresses "
        "(email, SMS, push tokens, Slack, Teams), system properties ($timezone, $locale), "
        "and custom key-value properties."
    )
    args_schema = GetUserInput
    permission_category = "subscribers"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."

        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.users.get, distinct_id)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching user '{distinct_id}'")


# ── GetUserPreferenceTool ─────────────────────────────────────────────────────

class GetUserPreferenceInput(BaseModel):
    distinct_id: str = Field(
        description="Unique identifier of the user whose preferences should be fetched."
    )
    category: str = Field(
        default="",
        description=(
            "Category slug to fetch preference for a single category. "
            "Leave empty to fetch full preferences across all categories."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )
    tenant_id: str = Field(
        default="",
        description="Tenant ID to scope preferences. Uses configured default if omitted.",
    )
    show_opt_out_channels: bool = Field(
        default=True,
        description=(
            "When True, includes the channel-level breakdown for opt-out categories. "
            "Set to False to skip channel details for categories the user has opted out of. "
            "Applies only when fetching full preferences (no category specified)."
        ),
    )
    tags: str = Field(
        default="",
        description=(
            "Filter preference categories by tags. Accepts a plain tag string (e.g. 'admin') "
            "or a nested JSON logical expression using and/or/not/exists operators "
            "(e.g. '{\"and\": [\"admin\", \"sales\"]}'). "
            "Applies only when fetching full preferences (no category specified)."
        ),
    )
    locale: str = Field(
        default="",
        description=(
            "Locale code to return category and section names in the user's language "
            "(e.g. 'es', 'es-AR'). Falls back to 'en' if the locale is unavailable. "
            "Applies only when fetching full preferences (no category specified)."
        ),
    )


class GetUserPreferenceTool(SuprSendTool):
    """GET {base_url}/v1/user/{distinct_id}/preference/"""

    name = "get_user_preference"
    description = (
        "Fetches the complete notification preference profile for a user — both category-level "
        "opt-in/out status across all sections, and overall channel-level restrictions. "
        "Use this to power a preference center UI or to debug why a user isn't receiving "
        "notifications on a particular channel or category. "
        "Pass a category slug to fetch preferences for that specific category only."
    )
    args_schema = GetUserPreferenceInput
    permission_category = "subscribers"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        category: str = "",
        show_opt_out_channels: bool = True,
        tags: str = "",
        locale: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        tenant = self._tenant_id(client, kwargs)

        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."

        try:
            sdk = await client.get_sdk_instance(ws)
            options: dict = {}
            if tenant:
                options["tenant_id"] = tenant
            if category:
                result = await asyncio.to_thread(
                    sdk.users.get_category_preference, distinct_id, category, options or None
                )
            else:
                if not show_opt_out_channels:
                    options["show_opt_out_channels"] = "false"
                if tags:
                    options["tags"] = tags
                if locale:
                    options["locale"] = locale
                result = await asyncio.to_thread(
                    sdk.users.get_full_preference, distinct_id, options or None
                )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching preferences for user '{distinct_id}'")


# ── GetUserObjectSubscriptionsTool ────────────────────────────────────────────

class GetUserObjectSubscriptionsInput(BaseModel):
    distinct_id: str = Field(
        description="Unique identifier of the user whose object subscriptions should be fetched."
    )
    limit: int = Field(
        default=20,
        description="Number of results to return per page.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetUserObjectSubscriptionsTool(SuprSendTool):
    """GET {base_url}/v1/user/{distinct_id}/subscribed_to/object/"""

    name = "get_user_object_subscriptions"
    description = (
        "Fetches all objects that a given user is subscribed to — the reverse lookup of "
        "get_object_subscriptions. Each result includes the object's details and the "
        "subscription-level properties set when the user was added as a subscriber. "
        "Use this to see which teams, departments, or other objects a user belongs to, "
        "or to debug why a user is receiving notifications from a particular object."
    )
    args_schema = GetUserObjectSubscriptionsInput
    permission_category = "subscribers"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        limit: int = 20,
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."

        try:
            sdk = await client.get_sdk_instance(ws)
            options: dict = {"limit": limit}
            result = await asyncio.to_thread(sdk.users.get_objects_subscribed_to, distinct_id, options)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching object subscriptions for user '{distinct_id}'")


# ── GetUserListSubscriptionsTool ──────────────────────────────────────────────

class GetUserListSubscriptionsInput(BaseModel):
    distinct_id: str = Field(
        description="Unique identifier of the user whose list subscriptions should be fetched."
    )
    limit: int = Field(
        default=20,
        description="Number of results to return per page.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetUserListSubscriptionsTool(SuprSendTool):
    """GET {base_url}/v1/user/{distinct_id}/subscribed_to/list/"""

    name = "get_user_list_subscriptions"
    description = (
        "Fetches all lists that a given user is part of. Each result includes list metadata "
        "and the timestamp when the user was added. Use this to see which broadcast lists "
        "a user belongs to, or to debug why a user is receiving broadcast notifications "
        "from a particular list."
    )
    args_schema = GetUserListSubscriptionsInput
    permission_category = "subscribers"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        limit: int = 20,
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."

        try:
            sdk = await client.get_sdk_instance(ws)
            options: dict = {"limit": limit}
            result = await asyncio.to_thread(sdk.users.get_lists_subscribed_to, distinct_id, options)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching list subscriptions for user '{distinct_id}'")


# ── CreateUserTool ────────────────────────────────────────────────────────────

class CreateUserInput(BaseModel):
    distinct_id: str = Field(
        description="Unique identifier of the user to create or update."
    )
    properties: dict = Field(
        default={},
        description=(
            "User properties to set. Supports system properties like $name, $email, $sms, "
            "$whatsapp, $androidpush, $iospush, $webpush, $slack, $ms_teams, $inbox, "
            "$timezone, $locale — and any custom key-value properties."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )

    @field_validator("properties", mode="before")
    @classmethod
    def parse_properties(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class CreateUserTool(SuprSendTool):
    """POST {base_url}/v1/user/{distinct_id}/"""

    name = "create_user"
    description = (
        "Create or fully replace a user profile. Provide the user's distinct_id and a properties "
        "dict containing channel addresses ($email, $sms, $whatsapp, etc.) and any custom fields. "
        "This is an upsert — if the user already exists their profile is replaced with the given properties."
    )
    args_schema = CreateUserInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        properties: dict = {},
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.users.upsert, distinct_id, properties)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"creating user '{distinct_id}'")


# ── UpdateUserTool ────────────────────────────────────────────────────────────

class UpdateUserInput(BaseModel):
    distinct_id: str = Field(
        description="Unique identifier of the user to update."
    )
    operations: list = Field(
        description=(
            "List of operation dicts to apply to the user. Each dict is one operation. "
            "Supported operations: "
            '$set — add/update properties e.g. {"$set": {"name": "Alice", "$timezone": "America/New_York"}}; '
            '$unset — remove properties or entire channels e.g. {"$unset": ["$sms", "old_prop"]}; '
            '$append — add a channel address e.g. {"$append": {"$email": "alice@example.com"}}; '
            '$remove — remove a specific channel address e.g. {"$remove": {"$email": "alice@example.com"}}; '
            '$set_once — set immutable property e.g. {"$set_once": {"first_seen": "2025-01-01"}}; '
            '$increment — numeric delta e.g. {"$increment": {"login_count": 1}}. '
            "Multiple operations can be combined in a single call."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )

    @field_validator("operations", mode="before")
    @classmethod
    def parse_operations(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class UpdateUserTool(SuprSendTool):
    """PATCH {base_url}/v1/user/{distinct_id}/"""

    name = "update_user"
    description = (
        "Apply partial updates to an existing user profile using operations. "
        "Use $set to add/overwrite properties, $unset to remove an entire channel or property, "
        "$append to add a specific channel address, $remove to remove a specific channel address, "
        "$set_once to set an immutable property, $increment for numeric counters. "
        "Multiple operations can be combined in one call."
    )
    args_schema = UpdateUserInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        operations: list = [],
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."
        if not operations:
            return "Error: operations list is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.users.edit, distinct_id, {"operations": operations})
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"updating user '{distinct_id}'")


# ── UpdateUserPreferenceCategoryTool ──────────────────────────────────────────

_VALID_CHANNELS = ["email", "sms", "whatsapp", "androidpush", "iospush", "webpush", "inbox", "slack", "ms_teams"]
_CHANNELS_DESC = ", ".join(f'"{c}"' for c in _VALID_CHANNELS)


class UpdateUserPreferenceCategoryInput(BaseModel):
    distinct_id: str = Field(description="Unique identifier of the user.")
    category: str = Field(description="Preference category slug to update.")
    preference: str = Field(
        description='Opt-in/out decision for the category. Must be "opt_in" or "opt_out".',
    )
    opt_in_channels: list = Field(
        default_factory=list,
        description=f"Channels to opt into for this category. Valid values: {_CHANNELS_DESC}.",
    )
    opt_out_channels: list = Field(
        default_factory=list,
        description=f"Channels to opt out of for this category. Valid values: {_CHANNELS_DESC}.",
    )
    tenant_id: str = Field(
        default="",
        description="Tenant scope for the preference update. Omit for the global (default) tenant.",
    )
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("opt_in_channels", "opt_out_channels", mode="before")
    @classmethod
    def parse_channels(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class UpdateUserPreferenceCategoryTool(SuprSendTool):
    """PATCH {base_url}/v1/user/{distinct_id}/preference/category/{category}/"""

    name = "update_user_preference_category"
    description = (
        "Update a user's opt-in or opt-out preference for a specific notification category. "
        "Set preference to 'opt_in' or 'opt_out' for the category as a whole. "
        "Optionally restrict the update to specific channels via opt_in_channels or opt_out_channels. "
        "Scope to a tenant with tenant_id to apply tenant-level preferences."
    )
    args_schema = UpdateUserPreferenceCategoryInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        category: str = "",
        preference: str = "",
        opt_in_channels: list = [],
        opt_out_channels: list = [],
        tenant_id: str = "",
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."
        if not category:
            return "Error: category is required."
        if preference not in ("opt_in", "opt_out"):
            return "Error: preference must be 'opt_in' or 'opt_out'."
        payload: dict = {"preference": preference}
        if opt_in_channels:
            payload["opt_in_channels"] = opt_in_channels
        if opt_out_channels:
            payload["opt_out_channels"] = opt_out_channels
        options = {"tenant_id": tenant_id} if tenant_id else None
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(
                sdk.users.update_category_preference, distinct_id, category, payload, options
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"updating category preference for user '{distinct_id}'")


# ── UpdateUserPreferenceChannelTool ───────────────────────────────────────────

class UpdateUserPreferenceChannelInput(BaseModel):
    distinct_id: str = Field(description="Unique identifier of the user.")
    channel_preferences: list = Field(
        description=(
            f"List of channel preference objects. Each item must have: "
            f'"channel" (one of {_CHANNELS_DESC}) and '
            f'"is_restricted" (bool — true blocks the channel, false enables it).'
        ),
    )
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("channel_preferences", mode="before")
    @classmethod
    def parse_channel_preferences(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class UpdateUserPreferenceChannelTool(SuprSendTool):
    """PATCH {base_url}/v1/user/{distinct_id}/preference/channel_preference/"""

    name = "update_user_preference_channel"
    description = (
        "Update a user's overall channel-level notification preferences. "
        "Set is_restricted=true to block a channel entirely for the user, false to enable it. "
        "Multiple channels can be updated in a single call."
    )
    args_schema = UpdateUserPreferenceChannelInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        channel_preferences: list = [],
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."
        if not channel_preferences:
            return "Error: channel_preferences list is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(
                sdk.users.update_channel_preference,
                distinct_id,
                {"channel_preferences": channel_preferences},
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"updating channel preferences for user '{distinct_id}'")

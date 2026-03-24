import asyncio
import yaml

import json

from pydantic import BaseModel, Field, field_validator

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool


# ── GetObjectTool ─────────────────────────────────────────────────────────────

class GetObjectInput(BaseModel):
    object_type: str = Field(
        description="Type of the object. Used to group similar objects together. Should be a plural namespace (e.g. 'departments', 'teams')."
    )
    object_id: str = Field(
        description="Unique identifier of the object within the given object_type."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetObjectTool(SuprSendTool):
    """GET {base_url}/v1/object/{object_type}/{object_id}/"""

    name = "get_object"
    description = (
        "Fetches the full profile of an object by its type and ID — including all channel "
        "configurations, custom properties, and the count of users or child objects subscribed "
        "to it. Objects are entities in your system (like teams, departments, or organizations) "
        "that can have notification channels and subscribers just like users."
    )
    args_schema = GetObjectInput
    permission_category = "subscribers"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        object_type: str = "",
        object_id: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not object_type:
            return "Error: object_type is required."
        if not object_id:
            return "Error: object_id is required."

        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.objects.get, object_type, object_id)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching object '{object_type}/{object_id}'")


# ── GetObjectPreferenceTool ───────────────────────────────────────────────────

class GetObjectPreferenceInput(BaseModel):
    object_type: str = Field(
        description="Type of the object. Should be a plural namespace (e.g. 'departments', 'teams')."
    )
    object_id: str = Field(
        description="Unique identifier of the object within the given object_type."
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


class GetObjectPreferenceTool(SuprSendTool):
    """GET {base_url}/v1/object/{object_type}/{object_id}/preference/"""

    name = "get_object_preference"
    description = (
        "Fetches the complete notification preference profile for an object — both category-level "
        "opt-in/out status across all categories, and overall channel-level restrictions. "
        "Identical in structure to get_user_preference but scoped to objects (teams, departments, "
        "organizations). Use this to inspect what notifications an object and its subscribers will "
        "receive, or to debug why an object isn't getting notifications on a particular channel or "
        "category. Pass a category slug to fetch preferences for that specific category only."
    )
    args_schema = GetObjectPreferenceInput
    permission_category = "subscribers"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        object_type: str = "",
        object_id: str = "",
        category: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        tenant = self._tenant_id(client, kwargs)

        if not ws:
            return "Error: workspace is required."
        if not object_type:
            return "Error: object_type is required."
        if not object_id:
            return "Error: object_id is required."

        try:
            sdk = await client.get_sdk_instance(ws)
            options = {"tenant_id": tenant} if tenant else {}
            if category:
                result = await asyncio.to_thread(
                    sdk.objects.get_category_preference, object_type, object_id, category, options or None
                )
            else:
                result = await asyncio.to_thread(
                    sdk.objects.get_full_preference, object_type, object_id, options or None
                )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching preferences for object '{object_type}/{object_id}'")


# ── GetObjectSubscriptionsTool ────────────────────────────────────────────────

class GetObjectSubscriptionsInput(BaseModel):
    object_type: str = Field(
        description="Type of the parent object. Should be a plural namespace (e.g. 'departments', 'teams')."
    )
    object_id: str = Field(
        description="Unique identifier of the parent object."
    )
    limit: int = Field(
        default=20,
        description="Number of subscriptions to return (max 100).",
    )
    cursor: str = Field(
        default="",
        description="Pagination cursor returned by a previous response.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetObjectSubscriptionsTool(SuprSendTool):
    """GET {base_url}/v1/object/{object_type}/{object_id}/subscription/"""

    name = "get_object_subscriptions"
    description = (
        "Returns a paginated list of all subscribers (users or child objects) attached to a given "
        "object. Each result shows either a user or an object subscriber, plus any subscription-level "
        "properties set when they were added. Subscription properties are accessible in workflow "
        "templates as $recipient.subscription.<key>."
    )
    args_schema = GetObjectSubscriptionsInput
    permission_category = "subscribers"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        object_type: str = "",
        object_id: str = "",
        limit: int = 20,
        cursor: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)

        if not ws:
            return "Error: workspace is required."
        if not object_type:
            return "Error: object_type is required."
        if not object_id:
            return "Error: object_id is required."

        try:
            options: dict = {"limit": limit}
            if cursor:
                options["cursor"] = cursor

            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(
                sdk.objects.get_subscriptions, object_type, object_id, options
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching subscriptions for object '{object_type}/{object_id}'")


# ── CreateObjectTool ──────────────────────────────────────────────────────────

class CreateObjectInput(BaseModel):
    object_type: str = Field(
        description="Type of the object. Should be a plural namespace (e.g. 'departments', 'teams')."
    )
    object_id: str = Field(
        description="Unique identifier of the object within the given object_type."
    )
    properties: dict = Field(
        default={},
        description=(
            "Object properties to set. Supports system properties like $name, $email, $sms, "
            "$whatsapp, $androidpush, $iospush, $webpush, $slack, $ms_teams, $inbox — "
            "and any custom key-value properties."
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


class CreateObjectTool(SuprSendTool):
    """POST {base_url}/v1/object/{object_type}/{object_id}/"""

    name = "create_object"
    description = (
        "Create or fully replace an object profile. Objects represent entities in your system "
        "(teams, departments, organizations) that can receive notifications and have subscribers. "
        "Provide object_type, object_id, and a properties dict. "
        "This is an upsert — if the object already exists its profile is replaced."
    )
    args_schema = CreateObjectInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        object_type: str = "",
        object_id: str = "",
        properties: dict = {},
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not object_type:
            return "Error: object_type is required."
        if not object_id:
            return "Error: object_id is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.objects.upsert, object_type, object_id, properties)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"creating object '{object_type}/{object_id}'")


# ── UpdateObjectTool ──────────────────────────────────────────────────────────

class UpdateObjectInput(BaseModel):
    object_type: str = Field(
        description="Type of the object. Should be a plural namespace (e.g. 'departments', 'teams')."
    )
    object_id: str = Field(
        description="Unique identifier of the object within the given object_type."
    )
    operations: list = Field(
        description=(
            "List of operation dicts to apply to the object. Each dict is one operation. "
            "Supported operations: "
            '$set — add/update non-channel properties e.g. {"$set": {"name": "Team Alpha", "$timezone": "UTC", "$locale": "es"}}. '
            "System properties: $timezone (IANA tz e.g. 'UTC'), $locale (language code e.g. 'en', 'es') "
            "— use $locale for language, NEVER $preferred_language or $language. "
            "NEVER use $set for channel addresses ($email, $sms, $whatsapp, etc.) — it will not work. "
            '$unset — remove an entire channel or property e.g. {"$unset": ["$email", "old_prop"]}; '
            '$append — add a channel address e.g. {"$append": {"$email": "team@example.com"}}; '
            '$remove — remove one specific channel address e.g. {"$remove": {"$email": "old@example.com"}}; '
            '$set_once — set immutable property e.g. {"$set_once": {"created_at": "2025-01-01"}}; '
            '$increment — numeric delta e.g. {"$increment": {"member_count": 1}}. '
            "Multiple operations can be combined in a single call. "
            "IMPORTANT — to change/replace a channel address (e.g. update email): "
            'use {"$unset": ["$email"]} followed by {"$append": {"$email": "new@example.com"}} in the same call. '
            "Never use $set, $add, or any other operation for channel updates."
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


class UpdateObjectTool(SuprSendTool):
    """PATCH {base_url}/v1/object/{object_type}/{object_id}/"""

    name = "update_object"
    description = (
        "Apply partial updates to an existing object using operations. "
        "For non-channel properties use $set. "
        "To add a channel address use $append. "
        "To remove a specific channel address use $remove. "
        "To remove an entire channel use $unset. "
        "To CHANGE/REPLACE a channel address (e.g. update email): "
        "combine $unset (remove the channel) + $append (add new address) in a single call. "
        "NEVER use $set for channel addresses — it does not work for channels."
    )
    args_schema = UpdateObjectInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        object_type: str = "",
        object_id: str = "",
        operations: list = [],
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not object_type:
            return "Error: object_type is required."
        if not object_id:
            return "Error: object_id is required."
        if not operations:
            return "Error: operations list is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.objects.edit, object_type, object_id, {"operations": operations})
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"updating object '{object_type}/{object_id}'")


# ── AddObjectSubscriptionTool ─────────────────────────────────────────────────

class AddObjectSubscriptionInput(BaseModel):
    object_type: str = Field(
        description="Type of the parent object. Should be a plural namespace (e.g. 'departments', 'teams')."
    )
    object_id: str = Field(
        description="Unique identifier of the parent object."
    )
    recipients: list = Field(
        description=(
            "List of recipients to subscribe. Each entry is either a user's distinct_id string, "
            'or an object reference dict like {"object_type": "teams", "id": "team_123"}.'
        ),
    )
    properties: dict = Field(
        default={},
        description=(
            "Subscription-level properties shared across all recipients in this call. "
            "Accessible in workflow templates as $recipient.subscription.<key>."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )

    @field_validator("recipients", "properties", mode="before")
    @classmethod
    def parse_json_fields(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class AddObjectSubscriptionTool(SuprSendTool):
    """POST {base_url}/v1/object/{object_type}/{object_id}/subscription/"""

    name = "add_object_subscription"
    description = (
        "Add one or more subscribers (users or child objects) to an object. "
        "Recipients can be user distinct_id strings or object reference dicts. "
        "Optional subscription-level properties are accessible in notification templates "
        "as $recipient.subscription.<key>."
    )
    args_schema = AddObjectSubscriptionInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        object_type: str = "",
        object_id: str = "",
        recipients: list = [],
        properties: dict = {},
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not object_type:
            return "Error: object_type is required."
        if not object_id:
            return "Error: object_id is required."
        if not recipients:
            return "Error: recipients list is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            payload = {"recipients": recipients, "properties": properties}
            result = await asyncio.to_thread(sdk.objects.create_subscriptions, object_type, object_id, payload)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"adding subscriptions to object '{object_type}/{object_id}'")


# ── UpdateObjectPreferenceCategoryTool ────────────────────────────────────────

_VALID_CHANNELS_OBJ = ["email", "sms", "whatsapp", "androidpush", "iospush", "webpush", "inbox", "slack", "ms_teams"]
_CHANNELS_DESC_OBJ = ", ".join(f'"{c}"' for c in _VALID_CHANNELS_OBJ)


class UpdateObjectPreferenceCategoryInput(BaseModel):
    object_type: str = Field(description="Type/namespace of the object.")
    object_id: str = Field(description="Unique identifier of the object within its type.")
    category: str = Field(description="Preference category slug to update.")
    preference: str = Field(
        description='Opt-in/out decision for the category. Must be "opt_in" or "opt_out".',
    )
    opt_in_channels: list = Field(
        default_factory=list,
        description=f"Channels to opt into for this category. Valid values: {_CHANNELS_DESC_OBJ}.",
    )
    opt_out_channels: list = Field(
        default_factory=list,
        description=f"Channels to opt out of for this category. Valid values: {_CHANNELS_DESC_OBJ}.",
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


class UpdateObjectPreferenceCategoryTool(SuprSendTool):
    """PATCH {base_url}/v1/object/{object_type}/{object_id}/preference/category/{category}/"""

    name = "update_object_preference_category"
    description = (
        "Update an object's opt-in or opt-out preference for a specific notification category. "
        "Set preference to 'opt_in' or 'opt_out' for the category as a whole. "
        "Optionally restrict to specific channels via opt_in_channels or opt_out_channels. "
        "Scope to a tenant with tenant_id for tenant-level preferences."
    )
    args_schema = UpdateObjectPreferenceCategoryInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        object_type: str = "",
        object_id: str = "",
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
        if not object_type:
            return "Error: object_type is required."
        if not object_id:
            return "Error: object_id is required."
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
                sdk.objects.update_category_preference, object_type, object_id, category, payload, options
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"updating category preference for object '{object_type}/{object_id}'")


# ── UpdateObjectPreferenceChannelTool ─────────────────────────────────────────

class UpdateObjectPreferenceChannelInput(BaseModel):
    object_type: str = Field(description="Type/namespace of the object.")
    object_id: str = Field(description="Unique identifier of the object within its type.")
    channel_preferences: list = Field(
        description=(
            f"List of channel preference objects. Each item must have: "
            f'"channel" (one of {_CHANNELS_DESC_OBJ}) and '
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


class UpdateObjectPreferenceChannelTool(SuprSendTool):
    """PATCH {base_url}/v1/object/{object_type}/{object_id}/preference/channel_preference/"""

    name = "update_object_preference_channel"
    description = (
        "Update an object's overall channel-level notification preferences. "
        "Set is_restricted=true to block a channel entirely for the object, false to enable it. "
        "Multiple channels can be updated in a single call."
    )
    args_schema = UpdateObjectPreferenceChannelInput
    permission_category = "subscribers"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        object_type: str = "",
        object_id: str = "",
        channel_preferences: list = [],
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not object_type:
            return "Error: object_type is required."
        if not object_id:
            return "Error: object_id is required."
        if not channel_preferences:
            return "Error: channel_preferences list is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(
                sdk.objects.update_channel_preference,
                object_type,
                object_id,
                {"channel_preferences": channel_preferences},
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"updating channel preferences for object '{object_type}/{object_id}'")

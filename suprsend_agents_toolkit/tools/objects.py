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
            return yaml.dump(result, default_flow_style=False)
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
            return yaml.dump(result, default_flow_style=False)
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
            return yaml.dump(result, default_flow_style=False)
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
            return yaml.dump(result, default_flow_style=False)
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
            '$set — add/update properties e.g. {"$set": {"name": "Team Alpha", "$timezone": "UTC"}}; '
            '$unset — remove properties or entire channels e.g. {"$unset": ["$sms", "old_prop"]}; '
            '$append — add a channel address e.g. {"$append": {"$email": "team@example.com"}}; '
            '$remove — remove a specific channel address e.g. {"$remove": {"$email": "team@example.com"}}; '
            '$set_once — set immutable property e.g. {"$set_once": {"created_at": "2025-01-01"}}; '
            '$increment — numeric delta e.g. {"$increment": {"member_count": 1}}. '
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


class UpdateObjectTool(SuprSendTool):
    """PATCH {base_url}/v1/object/{object_type}/{object_id}/"""

    name = "update_object"
    description = (
        "Apply partial updates to an existing object using operations. "
        "Use $set to add/overwrite properties, $unset to remove an entire channel or property, "
        "$append to add a specific channel address, $remove to remove a specific channel address, "
        "$set_once to set an immutable property, $increment for numeric counters. "
        "Multiple operations can be combined in one call."
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
            return yaml.dump(result, default_flow_style=False)
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
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"adding subscriptions to object '{object_type}/{object_id}'")

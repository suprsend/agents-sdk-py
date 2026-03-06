import asyncio
import yaml

from pydantic import BaseModel, Field

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
            return f"Error fetching object '{object_type}/{object_id}': {e}"


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
            return f"Error fetching preferences for object '{object_type}/{object_id}': {e}"


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
            return f"Error fetching subscriptions for object '{object_type}/{object_id}': {e}"

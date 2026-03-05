import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool


# ── GetObjectTool ─────────────────────────────────────────────────────────────

class GetObjectInput(BaseModel):
    object_type: str = Field(
        description="The type/category of the object (e.g. 'company', 'team')."
    )
    object_id: str = Field(
        description="The unique identifier of the object."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetObjectTool(SuprSendTool):
    """
    GET {base_url}/v1/object/{object_type}/{object_id}/

    Returns the full object profile: properties, channel identities,
    created_at, updated_at.
    """

    name = "get_object"
    description = (
        "Get all properties and channel identities for an object in SuprSend. "
        "Objects represent non-user entities such as companies, teams, or devices. "
        "Returns properties, channel addresses, and account timestamps."
    )
    args_schema = GetObjectInput
    permission_category = "subscribers"
    permission_operation = "read"

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
        description="The type/category of the object (e.g. 'company', 'team')."
    )
    object_id: str = Field(
        description="The unique identifier of the object."
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
    """
    Full preferences:
        GET {base_url}/v1/object/{object_type}/{object_id}/preference/?tenant_id=...
        Returns sections (categories + channels) and global channel preferences.

    Single category:
        GET {base_url}/v1/object/{object_type}/{object_id}/preference/category/{category}/?tenant_id=...
        Returns preference, opt-out channels, editability for that category.
    """

    name = "get_object_preference"
    description = (
        "Get notification preferences for an object. "
        "Omit category to get all preferences across every notification category. "
        "Pass a category slug to get preferences for that specific category only."
    )
    args_schema = GetObjectPreferenceInput
    permission_category = "subscribers"
    permission_operation = "read"

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
        description="The type/category of the object (e.g. 'company', 'team')."
    )
    object_id: str = Field(
        description="The unique identifier of the object."
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
    """
    GET {base_url}/v1/object/{object_type}/{object_id}/subscription/

    Returns a paginated list of subscribers (users or other objects) that are
    subscribed to receive notifications scoped to this object.
    Supports cursor-based pagination via `cursor` and `limit`.
    """

    name = "get_object_subscriptions"
    description = (
        "Get the list of subscribers for an object in SuprSend. "
        "Returns users or other objects subscribed to receive notifications "
        "related to this object. Supports cursor-based pagination."
    )
    args_schema = GetObjectSubscriptionsInput
    permission_category = "subscribers"
    permission_operation = "read"

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

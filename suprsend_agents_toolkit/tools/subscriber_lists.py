import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool

# ── GetSyncTaskSchemaTool ─────────────────────────────────────────────────────

class GetSyncTaskSchemaInput(BaseModel):
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetSyncTaskSchemaTool(SuprSendTool):
    """GET /v1/subscriber_sync_task_schema/"""

    name = "get_sync_task_schema"
    description = (
        "Return the database schema available for writing subscriber sync queries. "
        "Lists all tables (e.g. 'users', 'events') and their columns with data types. "
        "Call this first to understand what fields are queryable before writing a SQL query."
    )
    args_schema = GetSyncTaskSchemaInput
    permission_category = "lists"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(self, client: AsyncSuprSendClient, **kwargs) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.subscriber_sync.get_schema)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, "fetching sync task schema")


# ── CreateDynamicListTool ─────────────────────────────────────────────────────

class CreateDynamicListInput(BaseModel):
    list_id: str = Field(
        description="Required. Slug-style identifier for the list using only letters, numbers, hyphens, and underscores (e.g. 'active-users-2024'). Derived from the list name."
    )
    list_name: str = Field(
        description="Required. Human-readable display name for the list."
    )
    list_description: str = Field(
        default="",
        description="Optional description of what this list represents.",
    )
    track_user_entry: bool = Field(
        default=False,
        description="Fire an event when a user enters this list.",
    )
    track_user_exit: bool = Field(
        default=False,
        description="Fire an event when a user exits this list.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class CreateDynamicListTool(SuprSendTool):
    """POST /v1/subscriber_list/"""

    name = "create_dynamic_list"
    description = (
        "Create a new dynamic subscriber list. Members are filled by the list's sync task, "
        "which runs a SQL query. After creating the list, use dry_run_sync_query to validate a query, "
        "then update_sync_task_draft and publish_sync_task to make it live. "
        "If those tools report that the list has no sync task, call create_sync_task first."
    )
    args_schema = CreateDynamicListInput
    permission_category = "lists"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        list_name: str = "",
        list_description: str = "",
        track_user_entry: bool = False,
        track_user_exit: bool = False,
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not list_id:
            return "Error: list_id is required."
        if not list_name:
            return "Error: list_name is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            payload = {
                "list_id": list_id,
                "list_name": list_name,
                "list_type": "dynamic_list",
                "track_user_entry": track_user_entry,
                "track_user_exit": track_user_exit,
            }
            if list_description:
                payload["list_description"] = list_description
            result = await asyncio.to_thread(sdk.subscriber_lists.create, payload)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"creating dynamic list '{list_id}'")


# ── ListDynamicListsTool ──────────────────────────────────────────────────────

class ListDynamicListsInput(BaseModel):
    list_id: str = Field(
        default="",
        description="Filter by exact list ID. Omit to return all lists.",
    )
    list_type: str = Field(
        default="dynamic_list",
        description=(
            "Only return lists of these types: 'dynamic_list' (default), 'static_list', "
            "or both comma-separated ('static_list,dynamic_list'). Pass '' for all types."
        ),
    )
    limit: int = Field(
        default=20,
        description="Maximum number of results to return (default 20, max 1000).",
    )
    offset: int = Field(
        default=0,
        description="Pagination offset (default 0).",
    )
    is_enabled: str = Field(
        default="",
        description=(
            "Filter by enabled state. Omit for enabled lists only; "
            "'false' for disabled only; 'true,false' for all."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class ListDynamicListsTool(SuprSendTool):
    """GET /v1/subscriber_list/"""

    name = "list_dynamic_lists"
    description = (
        "List subscriber lists in the workspace. Filter by list_id or list_type. "
        "Returns metadata including subscriber count, status, and sync task configuration."
    )
    args_schema = ListDynamicListsInput
    permission_category = "lists"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        list_type: str = "dynamic_list",
        limit: int = 20,
        offset: int = 0,
        is_enabled: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            options = {}
            if list_id:
                options["list_id"] = list_id
            if is_enabled:
                options["is_enabled"] = is_enabled
            if list_type:
                options["list_type"] = list_type
            result = await asyncio.to_thread(sdk.subscriber_lists.get_all, limit, offset, options)
            # Servers without list_type support (before suprsend-api#691 is
            # deployed) ignore the param, so filter here too; this is a no-op
            # once the server filters. Items without a list_type field are kept.
            types = {t.strip() for t in list_type.split(",") if t.strip()}
            items = result.get("results") if isinstance(result, dict) else None
            if types and isinstance(items, list):
                result["results"] = [
                    i for i in items
                    if not isinstance(i, dict) or "list_type" not in i or i["list_type"] in types
                ]
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, "listing dynamic lists")


# ── GetListSubscribersTool ────────────────────────────────────────────────────

class GetListSubscribersInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list."
    )
    limit: int = Field(
        default=20,
        description="Maximum number of subscribers to return (default 20).",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetListSubscribersTool(SuprSendTool):
    """GET /v1/subscriber_list/{list_id}/subscriber/"""

    name = "get_list_subscribers"
    description = (
        "Return the subscribers currently in a subscriber list. "
        "Use this to verify that a sync task populated the list correctly after running."
    )
    args_schema = GetListSubscribersInput
    permission_category = "lists"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        limit: int = 20,
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not list_id:
            return "Error: list_id is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.subscriber_sync.get_list_subscribers, list_id, limit)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching subscribers for list '{list_id}'")

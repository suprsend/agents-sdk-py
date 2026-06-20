import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool

# ── CreateEventTool ───────────────────────────────────────────────────────────

class CreateEventInput(BaseModel):
    name: str = Field(
        description="Event name/identifier (e.g. 'user_signed_up')."
    )
    description: str = Field(
        default="",
        description="Optional description of what this event represents.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class CreateEventTool(SuprSendTool):
    """POST /v1/staging/event/"""

    name = "create_event"
    description = (
        "Create a new event definition in the workspace. "
        "Provide a unique event name and an optional description."
    )
    args_schema = CreateEventInput
    permission_category = "management"
    permission_subcategory = "events"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        name: str = "",
        description: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not name:
            return "Error: name is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.events.create, name, description)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"creating event '{name}'")


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
        "Create a new dynamic subscriber list. The list is automatically backed by a sync task "
        "that can be configured with a SQL query to populate members. "
        "After creating the list, use dry_run_sync_query to validate a query, "
        "then update_sync_task_draft and publish_sync_task to make it live."
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
            result = await asyncio.to_thread(
                sdk.subscriber_sync.create_list,
                list_id, list_name, list_description, track_user_entry, track_user_exit,
            )
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
            "Accepted for compatibility but NOT applied server-side — this endpoint "
            "does not support filtering by list type, so results may include other list types."
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
            result = await asyncio.to_thread(
                sdk.subscriber_sync.list_lists, list_type, limit, offset, list_id, is_enabled,
            )
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

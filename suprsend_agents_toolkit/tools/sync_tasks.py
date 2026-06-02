import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool


# ── DryRunSyncQueryTool ───────────────────────────────────────────────────────

class DryRunSyncQueryInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list whose sync task will be tested."
    )
    query_text: str = Field(
        description=(
            "SQL query to test. Must SELECT at least a 'distinct_id' column. "
            "Example: SELECT distinct_id FROM users WHERE active = true LIMIT 10"
        )
    )


class DryRunSyncQueryTool(SuprSendTool):
    """
    POST /v1/subscriber_sync_task/{list_id}/version/_/dry_run/
    POST /v1/subscriber_sync_task/{list_id}/version/_/dry_run/count/
    """

    name = "dry_run_sync_query"
    description = (
        "Preview and validate a SQL query before saving it to a sync task. "
        "Returns a sample of matched rows (up to the LIMIT in the query) and the total count. "
        "Use this to verify the query is correct before calling update_sync_task_draft."
    )
    args_schema = DryRunSyncQueryInput
    permission_category = "lists"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        query_text: str = "",
        **kwargs,
    ) -> str:
        if not list_id:
            return "Error: list_id is required."
        if not query_text:
            return "Error: query_text is required."
        try:
            base = f"{client.base_url}/v1/subscriber_sync_task/{list_id}/version/_/dry_run"
            payload = {"query_text": query_text}
            rows_result = await client.post(f"{base}/", payload)
            count_result = await client.post(f"{base}/count/", payload)
            combined = {
                "sample_data": rows_result.get("data", []),
                "total_count": count_result.get("count", 0),
            }
            return yaml.dump(combined, default_flow_style=False), combined
        except Exception as e:
            return self._api_error(e, f"dry running query for list '{list_id}'")


# ── GetSyncTaskTool ───────────────────────────────────────────────────────────

class GetSyncTaskInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list."
    )


class GetSyncTaskTool(SuprSendTool):
    """GET /v1/subscriber_sync_task/{list_id}/"""

    name = "get_sync_task"
    description = (
        "Get the current state of a subscriber list sync task, including its active query version, "
        "last sync status, last run time, and current execution status. "
        "Use this to check whether a sync completed successfully."
    )
    args_schema = GetSyncTaskInput
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
        **kwargs,
    ) -> str:
        if not list_id:
            return "Error: list_id is required."
        try:
            url = f"{client.base_url}/v1/subscriber_sync_task/{list_id}/"
            result = await client.get(url)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching sync task for list '{list_id}'")


# ── GetSyncTaskDraftTool ──────────────────────────────────────────────────────

class GetSyncTaskDraftInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list."
    )


class GetSyncTaskDraftTool(SuprSendTool):
    """GET /v1/subscriber_sync_task/{list_id}/version/_/"""

    name = "get_sync_task_draft"
    description = (
        "Get the current draft (unpublished) version of a sync task's query configuration. "
        "Returns the draft query_text, update_type, and column_mappings before they are published."
    )
    args_schema = GetSyncTaskDraftInput
    permission_category = "lists"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        **kwargs,
    ) -> str:
        if not list_id:
            return "Error: list_id is required."
        try:
            url = f"{client.base_url}/v1/subscriber_sync_task/{list_id}/version/_/"
            result = await client.get(url)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching draft version for list '{list_id}'")


# ── GetSyncTaskExecutionsTool ─────────────────────────────────────────────────

class GetSyncTaskExecutionsInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list."
    )
    limit: int = Field(
        default=10,
        description="Maximum number of executions to return, ordered newest first (default 10).",
    )


class GetSyncTaskExecutionsTool(SuprSendTool):
    """GET /v1/task_request/?list_id={list_id}"""

    name = "get_sync_task_executions"
    description = (
        "List the execution history for a subscriber list sync task, ordered newest first. "
        "Each execution shows its status (created, running, completed, failed, ignored), "
        "progress, and failure reason if applicable."
    )
    args_schema = GetSyncTaskExecutionsInput
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
        limit: int = 10,
        **kwargs,
    ) -> str:
        if not list_id:
            return "Error: list_id is required."
        try:
            url = f"{client.base_url}/v1/task_request/"
            result = await client.get(url, params={"list_id": list_id, "limit": limit})
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching executions for list '{list_id}'")


# ── UpdateSyncTaskDraftTool ───────────────────────────────────────────────────

class UpdateSyncTaskDraftInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list."
    )
    query_text: str = Field(
        description=(
            "SQL query that selects subscribers. Must include a 'distinct_id' column. "
            "Example: SELECT distinct_id FROM users WHERE plan = 'pro'"
        )
    )
    update_type: str = Field(
        default="replace",
        description="How to update the list on each sync. 'replace' replaces all members with query results.",
    )
    column_mappings: list = Field(
        default=[],
        description="Optional column mappings for profile sync. Leave empty for standard distinct_id-only queries.",
    )


class UpdateSyncTaskDraftTool(SuprSendTool):
    """PATCH /v1/subscriber_sync_task/{list_id}/version/_/"""

    name = "update_sync_task_draft"
    description = (
        "Save a SQL query to the draft version of a sync task. "
        "This does NOT make the query live — call publish_sync_task afterwards to activate it. "
        "Use dry_run_sync_query first to validate the query before saving."
    )
    args_schema = UpdateSyncTaskDraftInput
    permission_category = "lists"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        query_text: str = "",
        update_type: str = "replace",
        column_mappings: list = [],
        **kwargs,
    ) -> str:
        if not list_id:
            return "Error: list_id is required."
        if not query_text:
            return "Error: query_text is required."
        try:
            url = f"{client.base_url}/v1/subscriber_sync_task/{list_id}/version/_/"
            payload = {
                "query_text": query_text,
                "update_type": update_type,
                "column_mappings": column_mappings,
            }
            result = await client.patch(url, payload)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"updating draft for list '{list_id}'")


# ── PublishSyncTaskTool ───────────────────────────────────────────────────────

class PublishSyncTaskInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list."
    )
    query_text: str = Field(
        description="SQL query to publish as the active version."
    )
    update_type: str = Field(
        default="replace",
        description="How to update the list on each sync. Default is 'replace'.",
    )
    column_mappings: list = Field(
        default=[],
        description="Optional column mappings for profile sync.",
    )


class PublishSyncTaskTool(SuprSendTool):
    """PATCH /v1/subscriber_sync_task/{list_id}/version/_/ with status=active"""

    name = "publish_sync_task"
    description = (
        "Publish the sync task query, making it the active version. "
        "After publishing, call run_sync_now to immediately populate the list, "
        "or the query will run on the configured schedule."
    )
    args_schema = PublishSyncTaskInput
    permission_category = "lists"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        query_text: str = "",
        update_type: str = "replace",
        column_mappings: list = [],
        **kwargs,
    ) -> str:
        if not list_id:
            return "Error: list_id is required."
        if not query_text:
            return "Error: query_text is required."
        try:
            url = f"{client.base_url}/v1/subscriber_sync_task/{list_id}/version/_/"
            payload = {
                "query_text": query_text,
                "update_type": update_type,
                "column_mappings": column_mappings,
                "status": "active",
            }
            result = await client.patch(url, payload)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"publishing sync task for list '{list_id}'")


# ── RunSyncNowTool ────────────────────────────────────────────────────────────

class RunSyncNowInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list to sync immediately."
    )


class RunSyncNowTool(SuprSendTool):
    """POST /v1/subscriber_sync_task/{list_id}/schedule_now/"""

    name = "run_sync_now"
    description = (
        "Trigger an immediate sync run for a subscriber list. "
        "The sync task must have an active query version (published via publish_sync_task). "
        "Use get_sync_task or get_sync_task_executions to monitor progress."
    )
    args_schema = RunSyncNowInput
    permission_category = "lists"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        **kwargs,
    ) -> str:
        if not list_id:
            return "Error: list_id is required."
        try:
            url = f"{client.base_url}/v1/subscriber_sync_task/{list_id}/schedule_now/"
            result = await client.post(url, {})
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"scheduling sync now for list '{list_id}'")


# ── ToggleSyncTaskTool ────────────────────────────────────────────────────────

class ToggleSyncTaskInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list."
    )
    is_enabled: bool = Field(
        description="True to enable the sync task (allow scheduled runs), False to disable it."
    )


class ToggleSyncTaskTool(SuprSendTool):
    """PATCH /v1/subscriber_sync_task/{list_id}/"""

    name = "toggle_sync_task"
    description = (
        "Enable or disable a subscriber list sync task. "
        "When disabled, scheduled syncs will not run. "
        "Use is_enabled=true to re-enable a paused sync task."
    )
    args_schema = ToggleSyncTaskInput
    permission_category = "lists"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        is_enabled: bool = True,
        **kwargs,
    ) -> str:
        if not list_id:
            return "Error: list_id is required."
        try:
            url = f"{client.base_url}/v1/subscriber_sync_task/{list_id}/"
            result = await client.patch(url, {"is_enabled": is_enabled})
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            action = "enabling" if is_enabled else "disabling"
            return self._api_error(e, f"{action} sync task for list '{list_id}'")

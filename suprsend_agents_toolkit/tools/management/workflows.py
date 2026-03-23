import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool


# ── ListWorkflowsTool ─────────────────────────────────────────────────────────

class ListWorkflowsInput(BaseModel):
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )
    search: str = Field(
        default="",
        description="Search workflows by name, slug, or description.",
    )
    slugs: list[str] = Field(
        default_factory=list,
        description="Filter to specific workflow slugs. Multiple slugs are OR-combined.",
    )
    include_archived: bool = Field(
        default=False,
        description="When True, include archived workflows in the results.",
    )
    order_by: str = Field(
        default="",
        description=(
            "Sort order. Accepted values: 'last_executed_at', '-last_executed_at', "
            "'updated_at', '-updated_at'. Prefix '-' means descending."
        ),
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of workflows to return (1–50).",
    )
    offset: int = Field(
        default=0,
        description="Number of workflows to skip for pagination.",
    )


class ListWorkflowsTool(ManagementTool):
    """GET {mgmnt_url}/v1/{ws}/workflow/"""

    name = "list_workflows"
    description = (
        "List notification workflows created via the SuprSend dashboard UI. "
        "SuprSend supports three workflow types: (1) Event-triggered — the app publishes a named "
        "event and SuprSend routes it to matching workflows, decoupling the app from notification "
        "logic; (2) API-triggered — the app calls workflows.trigger() with a slug, recipients, "
        "and data, giving direct control over which workflow fires; (3) Dynamic — the entire "
        "workflow structure (steps, channels, templates) is defined inline in the API request at "
        "runtime, requiring no pre-configured dashboard workflow. "
        "Supports full-text search by name or slug, filtering to specific slugs, and sorting by "
        "last execution or update time. Use this to discover which workflows exist before "
        "fetching details or triggering one."
    )
    args_schema = ListWorkflowsInput
    permission_subcategory = "workflows"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        search: str = "",
        slugs: list = None,
        include_archived: bool = False,
        order_by: str = "",
        limit: int = 10,
        offset: int = 0,
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.workflows.list,
                ws,
                search=search or None,
                slugs=slugs or None,
                include_archived=include_archived,
                order_by=order_by or None,
                limit=limit,
                offset=offset,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"listing workflows for workspace '{ws}'")


# ── GetWorkflowTool ───────────────────────────────────────────────────────────

class GetWorkflowInput(BaseModel):
    workflow_slug: str = Field(
        description="The workflow slug identifier.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetWorkflowTool(ManagementTool):
    """GET {mgmnt_url}/v1/{ws}/workflow/{workflow_slug}/"""

    name = "get_workflow"
    description = (
        "Fetch the full details of a single workflow by its slug — including trigger type, "
        "status, steps, templates used, and last execution metadata."
    )
    args_schema = GetWorkflowInput
    permission_subcategory = "workflows"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        workflow_slug: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not workflow_slug:
            return "Error: workflow_slug is required."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.workflows.get,
                ws,
                workflow_slug,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching workflow '{workflow_slug}'")


# ── PushWorkflowTool ──────────────────────────────────────────────────────────

class PushWorkflowInput(BaseModel):
    workflow_slug: str = Field(description="Slug of the workflow to create or update.")
    workflow: dict = Field(description="Full workflow definition as a dict (same shape as get_workflow response).")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class PushWorkflowTool(ManagementTool):
    """POST {mgmnt_url}/v1/{ws}/workflow/{workflow_slug}/"""

    name = "push_workflow"
    description = (
        "Create or update a workflow definition as a draft. Accepts the full workflow dict "
        "(same shape returned by get_workflow). "
        "Automatically validates the definition before saving — returns validation errors "
        "without writing to the database if the definition is invalid. "
        "Always saves as draft. Use commit_workflow to deploy to live."
    )
    args_schema = PushWorkflowInput
    permission_subcategory = "workflows"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        workflow_slug: str = "",
        workflow: dict = None,
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not workflow_slug:
            return "Error: workflow_slug is required."
        if not workflow:
            return "Error: workflow definition is required."
        try:
            mgmt, headers = self._mgmnt(client)
            # Validate before saving — does not write to the database
            validation = await asyncio.to_thread(
                mgmt.workflows.validate,
                ws,
                workflow_slug,
                workflow,
                extra_headers=headers,
            )
            if not validation.get("is_valid", True):
                errors = validation.get("errors", [])
                result = {"validation_failed": True, "errors": errors}
                return yaml.dump(result, default_flow_style=False), result
            result = await asyncio.to_thread(
                mgmt.workflows.push,
                ws,
                workflow_slug,
                workflow,
                commit=False,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"pushing workflow '{workflow_slug}'")


# ── CommitWorkflowTool ────────────────────────────────────────────────────────

class CommitWorkflowInput(BaseModel):
    workflow_slug: str = Field(description="Slug of the workflow draft to commit to live.")
    commit_message: str = Field(default="", description="Optional message describing what changed.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class CommitWorkflowTool(ManagementTool):
    """PATCH {mgmnt_url}/v1/{ws}/workflow/{workflow_slug}/commit/"""

    name = "commit_workflow"
    description = (
        "Promote a saved workflow draft to live (deploy it). "
        "Call this ONLY after push_workflow has saved a valid draft. "
        "This is the final deployment step — it will trigger HitL confirmation."
    )
    args_schema = CommitWorkflowInput
    permission_subcategory = "workflows"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        workflow_slug: str = "",
        commit_message: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not workflow_slug:
            return "Error: workflow_slug is required."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.workflows.commit,
                ws,
                workflow_slug,
                commit_message=commit_message,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"committing workflow '{workflow_slug}'")

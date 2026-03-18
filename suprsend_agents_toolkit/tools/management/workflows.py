import json
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
        description="Maximum number of workflows to return (max 50).",
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
            result = await self._mgmnt_run(
                client,
                lambda mgmt, **kw: mgmt.workflows.list(
                    kw.pop("workspace"),
                    search=kw.pop("search") or None,
                    slugs=kw.pop("slugs") or None,
                    include_archived=kw.pop("include_archived"),
                    order_by=kw.pop("order_by") or None,
                    limit=kw.pop("limit"),
                    offset=kw.pop("offset"),
                    **kw,
                ),
                workspace=ws,
                search=search,
                slugs=slugs or [],
                include_archived=include_archived,
                order_by=order_by,
                limit=limit,
                offset=offset,
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return f"Error listing workflows for workspace '{ws}': {e}"


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
            result = await self._mgmnt_run(
                client,
                lambda mgmt, **kw: mgmt.workflows.get(
                    kw.pop("workspace"),
                    kw.pop("workflow_slug"),
                    **kw,
                ),
                workspace=ws,
                workflow_slug=workflow_slug,
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return f"Error fetching workflow '{workflow_slug}': {e}"


# ── PushWorkflowTool ──────────────────────────────────────────────────────────

class PushWorkflowInput(BaseModel):
    workflow_slug: str = Field(description="Slug of the workflow to create or update.")
    workflow: dict = Field(description="Full workflow definition as a dict (same shape as get_workflow response).")
    commit: bool = Field(default=False, description="False = save as draft (default). True = validate and deploy immediately.")
    commit_message: str = Field(default="", description="Optional message describing the changes.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class PushWorkflowTool(ManagementTool):
    """POST {mgmnt_url}/v1/{ws}/workflow/{workflow_slug}/"""

    name = "push_workflow"
    description = (
        "Create or update a workflow definition. Accepts the full workflow dict "
        "(same shape returned by get_workflow). "
        "Use commit=False (default) to save as draft for validation; "
        "use commit=True to deploy immediately. "
        "Always use commit=False first to validate the workflow structure."
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
        commit: bool = False,
        commit_message: str = "",
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
            result = await self._mgmnt_run(
                client,
                lambda mgmt, **kw: mgmt.workflows.push(
                    kw.pop("workspace"),
                    kw.pop("workflow_slug"),
                    kw.pop("workflow"),
                    commit=kw.pop("commit"),
                    commit_message=kw.pop("commit_message"),
                    **kw,
                ),
                workspace=ws,
                workflow_slug=workflow_slug,
                workflow=workflow,
                commit=commit,
                commit_message=commit_message,
            )
            return json.dumps(result)
        except Exception as e:
            return f"Error pushing workflow '{workflow_slug}': {e}"


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
            result = await self._mgmnt_run(
                client,
                lambda mgmt, **kw: mgmt.workflows.commit(
                    kw.pop("workspace"),
                    kw.pop("workflow_slug"),
                    commit_message=kw.pop("commit_message"),
                    **kw,
                ),
                workspace=ws,
                workflow_slug=workflow_slug,
                commit_message=commit_message,
            )
            return json.dumps(result)
        except Exception as e:
            return f"Error committing workflow '{workflow_slug}': {e}"

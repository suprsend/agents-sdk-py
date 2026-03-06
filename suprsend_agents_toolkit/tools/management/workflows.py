import yaml
from typing import List

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
    slugs: List[str] = Field(
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


class ListWorkflowsTool(ManagementTool):
    """GET {mgmnt_url}/v1/{ws}/workflow/"""

    name = "list_workflows"
    description = (
        "List workflows in the workspace. Supports full-text search by name or slug, "
        "filtering to specific slugs, and sorting by last execution or update time. "
        "Use this to discover which workflows exist before fetching details or triggering one."
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
                    **kw,
                ),
                workspace=ws,
                search=search,
                slugs=slugs or [],
                include_archived=include_archived,
                order_by=order_by,
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

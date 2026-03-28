import asyncio
import yaml
from typing import Union

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool
from suprsend_agents_toolkit.tools._utils import evaluate_jsonnet, validate_with_jsonpath


class ValidateSchemaInput(BaseModel):
    workflow_slug: str = Field(
        default="",
        description="Workflow slug to validate against. Provide this OR event_name.",
    )
    event_name: str = Field(
        default="",
        description="Event name to validate against. Provide this OR workflow_slug.",
    )
    data: Union[dict, str] = Field(
        default_factory=dict,
        description=(
            "Data/properties to validate. Either a plain dict or a Jsonnet template string. "
            "Jsonnet is evaluated before validation."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class ValidateSchemaTool(ManagementTool):
    name = "validate_schema"
    description = (
        "Validate a data payload against a workflow's trigger_inputs or event's payload_schema "
        "WITHOUT triggering anything. Use this to dry-run a payload before calling trigger_workflow "
        "or track_event. Accepts plain dicts or Jsonnet template strings for data. "
        "Supports JSONPath field references in the schema."
    )
    args_schema = ValidateSchemaInput
    permission_category = "management"
    permission_subcategory = "events"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        workflow_slug: str = "",
        event_name: str = "",
        data: Union[dict, str] = None,
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."

        if not workflow_slug and not event_name:
            return "Error: provide either workflow_slug or event_name."
        if workflow_slug and event_name:
            return "Error: provide either workflow_slug or event_name, not both."

        data = data or {}

        # Evaluate Jsonnet if needed
        try:
            data = evaluate_jsonnet(data)
        except (ImportError, ValueError) as e:
            return f"Error evaluating data: {e}"

        # Fetch schema
        schema = {}
        try:
            mgmt, headers = self._mgmnt(client)
            if workflow_slug:
                result = await asyncio.to_thread(
                    mgmt.workflows.get, ws, workflow_slug, extra_headers=headers
                )
                schema = result.get("trigger_inputs") or {}
            else:
                result = await asyncio.to_thread(
                    mgmt.events.get, ws, event_name, extra_headers=headers
                )
                schema = result.get("payload_schema") or {}
        except Exception as e:
            target = workflow_slug or event_name
            return self._api_error(e, f"fetching schema for '{target}'")

        if not schema:
            return "No schema defined for this workflow/event — any payload is accepted."

        error = validate_with_jsonpath(data, schema)

        target = {"workflow": workflow_slug} if workflow_slug else {"event": event_name}
        summary = {
            "valid": error is None,
            "target": target,
            "data": data,
            "errors": error,
            "schema": schema,
        }
        return yaml.dump(summary, default_flow_style=False), summary
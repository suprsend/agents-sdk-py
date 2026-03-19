import asyncio
import uuid
from typing import Union
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool
from suprsend_agents_toolkit.tools._utils import evaluate_jsonnet, validate_with_jsonpath

try:
    from suprsend.workflow_request import WorkflowTriggerRequest
except ImportError:
    WorkflowTriggerRequest = None  # type: ignore[assignment,misc]


# Backward-compat alias — kept in case external code imports _validate_trigger_data
def _validate_trigger_data(data: dict, trigger_inputs: dict) -> str | None:
    return validate_with_jsonpath(data, trigger_inputs)


class TriggerWorkflowInput(BaseModel):
    workflow_slug: str = Field(
        description="The slug of the API-triggered workflow to run."
    )
    recipients: list = Field(
        description=(
            "List of recipients. Each entry is either a distinct_id string "
            "or a user object with at least a distinct_id key."
        )
    )
    data: Union[dict, str] = Field(
        default_factory=dict,
        description=(
            "Key-value pairs passed as workflow data. Either a plain dict or a Jsonnet template string. "
            "Must satisfy the workflow's trigger_inputs schema. "
            "Call get_workflow first to see which fields are required."
        ),
    )
    tenant_id: str = Field(
        default="",
        description="Optional tenant context for the trigger call.",
    )
    idempotency_key: str = Field(
        default="",
        description="Optional idempotency key to deduplicate trigger calls.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class TriggerWorkflowTool(ManagementTool):
    """POST {base_url}/v1/workflow/trigger/"""

    name = "trigger_workflow"
    description = (
        "Trigger an API-triggered SuprSend workflow. "
        "Always call get_workflow first to see the required trigger_inputs schema and "
        "understand what data fields must be provided. "
        "If the workflow defines trigger_inputs, this tool validates the data dict against "
        "that schema and returns an error with the full schema if validation fails."
    )
    args_schema = TriggerWorkflowInput
    permission_category = "workflows"
    permission_subcategory = None
    permission_operation = "trigger"
    read_only = False
    destructive = False
    idempotent = False
    open_world = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        workflow_slug: str = "",
        recipients: list = None,
        data: Union[dict, str] = None,
        tenant_id: str = "",
        idempotency_key: str = "",
        **kwargs,
    ) -> str:
        if WorkflowTriggerRequest is None:
            return "Error: suprsend SDK not installed. Install suprsend to use this tool."

        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not workflow_slug:
            return "Error: workflow_slug is required."
        if not recipients:
            return "Error: recipients is required and must be a non-empty list."

        data = data or {}

        # Evaluate Jsonnet if needed
        try:
            data = evaluate_jsonnet(data)
        except (ImportError, ValueError) as e:
            return f"Error evaluating data: {e}"

        # Always use an idempotency key — generate one if not supplied
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Fetch workflow definition to get trigger_inputs schema
        try:
            mgmt, headers = self._mgmnt(client)
            workflow_def = await asyncio.to_thread(
                mgmt.workflows.get, ws, workflow_slug, extra_headers=headers
            )
        except Exception as e:
            return self._api_error(e, f"fetching workflow '{workflow_slug}'")

        trigger_inputs = workflow_def.get("trigger_inputs") or {}

        # Validate data against schema if one is defined
        if trigger_inputs:
            error = validate_with_jsonpath(data, trigger_inputs)
            if error:
                schema_yaml = yaml.dump(trigger_inputs, default_flow_style=False)
                return (
                    f"Validation error for workflow '{workflow_slug}':\n{error}\n\n"
                    f"Required trigger_inputs schema:\n{schema_yaml}"
                )

        # Trigger via SDK
        try:
            sdk = await client.get_sdk_instance(ws)
            body: dict = {
                "workflow": workflow_slug,
                "recipients": recipients,
                "data": data,
                "$idempotency_key": idempotency_key,
            }
            if tenant_id:
                body["tenant_id"] = tenant_id

            result = await asyncio.to_thread(
                sdk.workflows.trigger, WorkflowTriggerRequest(body)
            )
            summary: dict = {
                "triggered": {
                    "workflow": workflow_slug,
                    "workspace": ws,
                    "recipients": recipients,
                    "data": data,
                    "idempotency_key": idempotency_key,
                }
            }
            if tenant_id:
                summary["triggered"]["tenant_id"] = tenant_id
            summary["api_response"] = result
            return yaml.dump(summary, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"triggering workflow '{workflow_slug}'")
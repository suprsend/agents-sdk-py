import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool

try:
    from suprsend.workflow_request import WorkflowTriggerRequest
except ImportError:
    WorkflowTriggerRequest = None  # type: ignore[assignment,misc]


def _validate_trigger_data(data: dict, trigger_inputs: dict) -> str | None:
    """
    Validate data against the trigger_inputs schema.

    Handles two schema shapes:
    - {field: {type, required, description}}
    - {properties: {field: {type, required, description}}}

    Returns None if valid, or a descriptive error string listing issues.
    """
    # Unwrap JSON Schema-style envelope if present
    fields = trigger_inputs.get("properties") or trigger_inputs

    missing = []
    wrong_type = []

    for field_name, field_def in fields.items():
        if not isinstance(field_def, dict):
            continue
        required = field_def.get("required", False)
        expected_type = field_def.get("type", "")

        if required and field_name not in data:
            missing.append(field_name)
            continue

        if expected_type and field_name in data:
            value = data[field_name]
            type_map = {
                "string": str,
                "str": str,
                "integer": int,
                "int": int,
                "number": (int, float),
                "float": float,
                "boolean": bool,
                "bool": bool,
                "array": list,
                "list": list,
                "object": dict,
                "dict": dict,
            }
            expected_py = type_map.get(expected_type.lower())
            if expected_py and not isinstance(value, expected_py):
                wrong_type.append(
                    f"  {field_name}: expected {expected_type}, got {type(value).__name__}"
                )

    errors = []
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")
    if wrong_type:
        errors.append("Type mismatches:\n" + "\n".join(wrong_type))

    return "\n".join(errors) if errors else None


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
    data: dict = Field(
        default_factory=dict,
        description=(
            "Key-value pairs passed as workflow data. "
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
        data: dict = None,
        tenant_id: str = "",
        idempotency_key: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not workflow_slug:
            return "Error: workflow_slug is required."
        if not recipients:
            return "Error: recipients is required and must be a non-empty list."

        data = data or {}

        # Fetch workflow definition to get trigger_inputs schema
        try:
            workflow_def = await self._mgmnt_run(
                client,
                lambda mgmt, **kw: mgmt.workflows.get(
                    kw.pop("workspace"),
                    kw.pop("workflow_slug"),
                    **kw,
                ),
                workspace=ws,
                workflow_slug=workflow_slug,
            )
        except Exception as e:
            return f"Error fetching workflow '{workflow_slug}': {e}"

        trigger_inputs = workflow_def.get("trigger_inputs") or {}

        # Validate data against schema if one is defined
        if trigger_inputs:
            error = _validate_trigger_data(data, trigger_inputs)
            if error:
                schema_yaml = yaml.dump(trigger_inputs, default_flow_style=False)
                return (
                    f"Validation error for workflow '{workflow_slug}':\n{error}\n\n"
                    f"Required trigger_inputs schema:\n{schema_yaml}"
                )

        # Trigger via SDK
        try:
            if WorkflowTriggerRequest is None:
                return "Error: suprsend SDK not installed. Install suprsend to use this tool."

            sdk = await client.get_sdk_instance(ws)
            body: dict = {"workflow": workflow_slug, "recipients": recipients, "data": data}
            if tenant_id:
                body["tenant_id"] = tenant_id
            if idempotency_key:
                body["$idempotency_key"] = idempotency_key

            result = await asyncio.to_thread(
                sdk.workflows.trigger, WorkflowTriggerRequest(body)
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return f"Error triggering workflow '{workflow_slug}': {e}"
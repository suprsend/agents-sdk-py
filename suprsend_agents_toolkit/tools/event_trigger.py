import asyncio
import uuid
from typing import Union
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool
from suprsend_agents_toolkit.tools._utils import evaluate_jsonnet, validate_with_jsonpath

try:
    from suprsend.event import Event
except ImportError:
    Event = None  # type: ignore[assignment,misc]


class TrackEventInput(BaseModel):
    distinct_id: str = Field(
        description="The user to track the event for.",
    )
    event_name: str = Field(
        description="Name of the event to track. Must not start with '$' or 'ss_'.",
    )
    properties: Union[dict, str] = Field(
        default_factory=dict,
        description=(
            "Event payload key-value pairs. Either a plain dict or a Jsonnet template string. "
            "Must satisfy the event's payload schema if one is defined. "
            "Call get_event_details first to see which fields are required."
        ),
    )
    tenant_id: str = Field(
        default="",
        description="Optional tenant context for the event.",
    )
    idempotency_key: str = Field(
        default="",
        description="Optional idempotency key to deduplicate event calls.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class TrackEventTool(ManagementTool):
    """POST hub — sdk.track_event(Event(...))"""

    name = "track_event"
    description = (
        "Track a SuprSend event for a user. This fires all workflows that listen for the event. "
        "Call get_event_details first to see the payload schema and which workflows will be triggered. "
        "If the event defines a payload schema, this tool validates properties against it and returns "
        "an error with the full schema if validation fails."
    )
    args_schema = TrackEventInput
    permission_category = "events"
    permission_subcategory = None
    permission_operation = "trigger"
    read_only = False
    destructive = False
    idempotent = False
    open_world = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        event_name: str = "",
        properties: Union[dict, str] = None,
        tenant_id: str = "",
        idempotency_key: str = "",
        **kwargs,
    ) -> str:
        if Event is None:
            return "Error: suprsend SDK not installed. Install suprsend to use this tool."

        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."
        if not event_name:
            return "Error: event_name is required."

        properties = properties or {}

        # Evaluate Jsonnet if needed
        try:
            properties = evaluate_jsonnet(properties)
        except (ImportError, ValueError) as e:
            return f"Error evaluating properties: {e}"

        # Always use an idempotency key — generate one if not supplied
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Fetch event definition to get payload_schema
        try:
            mgmt, headers = self._mgmnt(client)
            event_def = await asyncio.to_thread(
                mgmt.events.get, ws, event_name, extra_headers=headers
            )
        except Exception as e:
            return self._api_error(
                e,
                f"fetching event '{event_name}' for schema validation"
                " — if using JWT auth, ensure api_secret is configured in ToolContext",
            )

        payload_schema = event_def.get("payload_schema") or {}

        # Validate properties against schema if one is defined
        if payload_schema:
            error = validate_with_jsonpath(properties, payload_schema)
            if error:
                schema_yaml = yaml.dump(payload_schema, default_flow_style=False)
                return (
                    f"Validation error for event '{event_name}':\n{error}\n\n"
                    f"Required payload schema:\n{schema_yaml}"
                )

        # Resolve tenant: explicit arg → context default → omit
        tenant = tenant_id or client.context.tenant_id or ""

        # Track via SDK
        try:
            sdk = await client.get_sdk_instance(ws)
            event = Event(
                distinct_id,
                event_name,
                properties,
                idempotency_key=idempotency_key,
                tenant_id=tenant or None,
            )
            result = await asyncio.to_thread(sdk.track_event, event)

            summary: dict = {
                "tracked": {
                    "event": event_name,
                    "distinct_id": distinct_id,
                    "workspace": ws,
                    "properties": properties,
                    "idempotency_key": idempotency_key,
                }
            }
            if tenant:
                summary["tracked"]["tenant_id"] = tenant
            summary["api_response"] = result
            return yaml.dump(summary, default_flow_style=False), summary
        except Exception as e:
            return self._api_error(e, f"tracking event '{event_name}'")
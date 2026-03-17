import asyncio
import uuid
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool
from suprsend_agents_toolkit.tools.workflow_trigger import _validate_trigger_data

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
    properties: dict = Field(
        default_factory=dict,
        description=(
            "Event payload key-value pairs. "
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
        properties: dict = None,
        tenant_id: str = "",
        idempotency_key: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."
        if not event_name:
            return "Error: event_name is required."

        properties = properties or {}
        # Always use an idempotency key — generate one if not supplied
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Fetch event definition to get payload_schema
        try:
            event_def = await self._mgmnt_run(
                client,
                lambda mgmt, **kw: mgmt.events.get(kw.pop("workspace"), kw.pop("event_name"), **kw),
                workspace=ws,
                event_name=event_name,
            )
        except Exception as e:
            return f"Error fetching event '{event_name}': {e}"

        payload_schema = event_def.get("payload_schema") or {}

        # Validate properties against schema if one is defined
        if payload_schema:
            error = _validate_trigger_data(properties, payload_schema)
            if error:
                schema_yaml = yaml.dump(payload_schema, default_flow_style=False)
                return (
                    f"Validation error for event '{event_name}':\n{error}\n\n"
                    f"Required payload schema:\n{schema_yaml}"
                )

        # Track via SDK
        try:
            if Event is None:
                return "Error: suprsend SDK not installed. Install suprsend to use this tool."

            sdk = await client.get_sdk_instance(ws)
            event = Event(
                distinct_id,
                event_name,
                properties,
                idempotency_key=idempotency_key,
                tenant_id=tenant_id or None,
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
            if tenant_id:
                summary["tracked"]["tenant_id"] = tenant_id
            summary["api_response"] = result
            return yaml.dump(summary, default_flow_style=False)
        except Exception as e:
            return f"Error tracking event '{event_name}': {e}"
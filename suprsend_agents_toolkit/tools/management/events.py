import asyncio
import yaml
from urllib.parse import quote

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool


class GetEventDetailsInput(BaseModel):
    event_name: str = Field(
        description="The event name (slug) to fetch details for.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetEventDetailsTool(ManagementTool):
    """GET {mgmnt_url}/v1/{ws}/event/{event_name}/"""

    name = "get_event_details"
    description = (
        "Fetch details of a single event by its name — including description, "
        "payload schema, associated workflows, and last triggered timestamp. "
        "Use this to understand what an event does and which workflows it triggers."
    )
    args_schema = GetEventDetailsInput
    permission_subcategory = "events"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        event_name: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not event_name:
            return "Error: event_name is required."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.events.get,
                ws,
                event_name,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching event '{event_name}' in workspace '{ws}'")


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


class CreateEventTool(ManagementTool):
    """POST {mgmnt_url}/v1/{ws}/event/"""

    name = "create_event"
    description = (
        "Create a new event definition in the workspace. "
        "Provide a unique event name and an optional description."
    )
    args_schema = CreateEventInput
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
            # Management API only (ServiceToken or dashboard JWT); hub has no
            # route for it, so the hub SDK can't create events.
            result = await self._mgmnt_post(
                client,
                f"/v1/{quote(ws, safe='')}/event/",
                {"name": name, "description": description},
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"creating event '{name}'")

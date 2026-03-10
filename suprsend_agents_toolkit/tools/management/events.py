import yaml

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
            result = await client.mgmnt_get(f"/v1/{ws}/event/{event_name}/")
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return f"Error fetching event '{event_name}' in workspace '{ws}': {e}"

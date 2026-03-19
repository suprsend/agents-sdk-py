import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool


class GetPreferenceCategoriesInput(BaseModel):
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetPreferenceCategoriesTool(ManagementTool):
    """GET {mgmnt_url}/v1/{ws}/notification_category/"""

    name = "get_preference_categories"
    description = (
        "List all notification preference categories defined in the workspace. "
        "Each category controls which notifications a subscriber can opt in or out of. "
        "Use this to understand what preference controls exist before modifying user preferences, "
        "or to build a preference centre UI."
    )
    args_schema = GetPreferenceCategoriesInput
    permission_subcategory = "preference_categories"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.preference_categories.list,
                ws,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"fetching preference categories for workspace '{ws}'")

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


# ── UpdatePreferenceCategoryTool ──────────────────────────────────────────────

class UpdatePreferenceCategoryInput(BaseModel):
    category_slug: str = Field(
        description="Slug identifier of the preference category to update."
    )
    name: str = Field(
        default="",
        description="Display name for the category.",
    )
    description: str = Field(
        default="",
        description="Description of the category shown in preference centers.",
    )
    default_preference: str = Field(
        default="",
        description="Default preference for users in this category: 'opt_in' or 'opt_out'.",
    )
    default_mandatory_channels: list = Field(
        default=[],
        description=(
            "Channels that cannot be opted out of for this category "
            "(e.g. ['email', 'sms']). Only applies when default_preference is 'opt_in'."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class UpdatePreferenceCategoryTool(ManagementTool):
    """PATCH {mgmnt_url}/v1/{ws}/preference_category/{category_slug}/"""

    name = "update_preference_category"
    description = (
        "Update the defaults for a notification preference category. "
        "You can change the display name, description, default opt-in/out preference, "
        "and which channels are mandatory (cannot be opted out). "
        "Only fields provided (non-empty) are included in the update."
    )
    args_schema = UpdatePreferenceCategoryInput
    permission_subcategory = "preference_categories"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        category_slug: str = "",
        name: str = "",
        description: str = "",
        default_preference: str = "",
        default_mandatory_channels: list = [],
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not category_slug:
            return "Error: category_slug is required."
        payload: dict = {}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if default_preference:
            if default_preference not in ("opt_in", "opt_out"):
                return "Error: default_preference must be 'opt_in' or 'opt_out'."
            payload["default_preference"] = default_preference
        if default_mandatory_channels:
            payload["default_mandatory_channels"] = default_mandatory_channels
        if not payload:
            return "Error: at least one field to update must be provided."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.preference_categories.update,
                ws,
                category_slug,
                payload,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"updating preference category '{category_slug}' in workspace '{ws}'")

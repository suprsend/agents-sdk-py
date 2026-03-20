import asyncio
import yaml

import json

from pydantic import BaseModel, Field, field_validator

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
    root_categories: list = Field(
        description=(
            "Full preference category tree to save. Must include all three root categories: "
            "'system', 'transactional', and 'promotional'. "
            "IMPORTANT: This is a full override — always call get_preference_categories first "
            "to fetch the current tree, modify the target category inside it, then pass the "
            "complete modified tree here. Omitting a root category will delete it."
        ),
    )
    commit: bool = Field(
        default=False,
        description="If True, changes go live immediately. If False (default), saves as a draft.",
    )
    commit_message: str = Field(
        default="",
        description="Description of the changes. Required when commit=True.",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )

    @field_validator("root_categories", mode="before")
    @classmethod
    def parse_root_categories(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class UpdatePreferenceCategoryTool(ManagementTool):
    """POST {mgmnt_url}/v1/{ws}/preference_category/"""

    name = "update_preference_category"
    description = (
        "Save an updated preference category tree for a workspace. "
        "This is a FULL OVERRIDE — always call get_preference_categories first to get the "
        "current tree, modify only the specific category you want to change, then pass the "
        "complete tree back here. "
        "Each category supports: category (slug), name, description, "
        "default_preference ('opt_in' | 'opt_out' | 'cant_unsubscribe'), "
        "default_mandatory_channels (list), default_opt_in_channels (list), tags (list). "
        "Set commit=True to deploy immediately, or leave False to save as a draft first."
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
        root_categories: list = [],
        commit: bool = False,
        commit_message: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not root_categories:
            return "Error: root_categories is required."
        if commit and not commit_message:
            return "Error: commit_message is required when commit=True."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.preference_categories.update,
                ws,
                root_categories,
                commit=commit,
                commit_message=commit_message,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"updating preference categories in workspace '{ws}'")

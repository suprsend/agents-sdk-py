import asyncio
import yaml

import json

from pydantic import BaseModel, Field, field_validator

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool


# ── AddUserToListTool ─────────────────────────────────────────────────────────

class AddUserToListInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list to add users to."
    )
    distinct_ids: list = Field(
        description="One or more user distinct_ids to add to the list."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )

    @field_validator("distinct_ids", mode="before")
    @classmethod
    def parse_distinct_ids(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class AddUserToListTool(SuprSendTool):
    """POST {base_url}v1/subscriber_list/{list_id}/subscriber/add/"""

    name = "add_user_to_list"
    description = (
        "Add one or more users to a subscriber list by their distinct_ids. "
        "The list must already exist. Multiple users can be added in a single call. "
        "Use this to enrol users into a broadcast or segment list."
    )
    args_schema = AddUserToListInput
    permission_category = "lists"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        distinct_ids: list = [],
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not list_id:
            return "Error: list_id is required."
        if not distinct_ids:
            return "Error: distinct_ids is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.subscriber_lists.add, list_id, distinct_ids)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"adding users to list '{list_id}'")


# ── RemoveUserFromListTool ────────────────────────────────────────────────────

class RemoveUserFromListInput(BaseModel):
    list_id: str = Field(
        description="Unique identifier of the subscriber list to remove users from."
    )
    distinct_ids: list = Field(
        description="One or more user distinct_ids to remove from the list."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )

    @field_validator("distinct_ids", mode="before")
    @classmethod
    def parse_distinct_ids(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class RemoveUserFromListTool(SuprSendTool):
    """POST {base_url}v1/subscriber_list/{list_id}/subscriber/remove/"""

    name = "remove_user_from_list"
    description = (
        "Remove one or more users from a subscriber list by their distinct_ids. "
        "Multiple users can be removed in a single call. "
        "Use this to unenrol users from a broadcast or segment list."
    )
    args_schema = RemoveUserFromListInput
    permission_category = "lists"
    permission_operation = "manage"
    read_only = False
    destructive = True
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        list_id: str = "",
        distinct_ids: list = [],
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not list_id:
            return "Error: list_id is required."
        if not distinct_ids:
            return "Error: distinct_ids is required."
        try:
            sdk = await client.get_sdk_instance(ws)
            result = await asyncio.to_thread(sdk.subscriber_lists.remove, list_id, distinct_ids)
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"removing users from list '{list_id}'")

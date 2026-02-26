import json
import os
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

_DEBUG_LOG = "/tmp/suprsend_debug.log"

def _debug(msg: str) -> None:
    import sys
    from datetime import datetime
    line = f"{datetime.utcnow().isoformat()} {msg}\n"
    print(line, flush=True)
    sys.stderr.write(line)
    sys.stderr.flush()
    try:
        with open(_DEBUG_LOG, "a") as f:
            f.write(line)
    except Exception:
        pass

from pydantic import BaseModel, Field

from suprsend_agents.client import AsyncSuprSendClient
from suprsend_agents.core.base import SuprSendTool


# ── GetUserTool ───────────────────────────────────────────────────────────────

class GetUserInput(BaseModel):
    distinct_id: str = Field(
        description="The unique identifier of the user."
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetUserTool(SuprSendTool):
    """
    GET {base_url}/v1/user/{distinct_id}/

    Returns the full user profile: properties, channel identities
    ($email, $sms, $whatsapp, push, $slack, etc.), created_at, updated_at.
    """

    name = "get_user"
    description = (
        "Get all properties and channel identities for a user in SuprSend. "
        "Returns properties, channel addresses (email, SMS, WhatsApp, push, Slack), "
        "and account timestamps."
    )
    args_schema = GetUserInput
    permission_category = "subscribers"
    permission_operation = "read"

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."

        try:
            path = f"v1/user/{quote(distinct_id, safe='')}/"
            url = f"{client.base_url}/{path}"
            _debug(f"[get_user] workspace={ws} url={url} auth={type(client.auth).__name__}")
            result = await client.workspace_get(ws, path)
            _debug("[get_user] success")
            return json.dumps(result, indent=2)
        except Exception as e:
            _debug(f"[get_user] error: {e}")
            return f"Error fetching user '{distinct_id}': {e}"


# ── GetUserPreferenceTool ─────────────────────────────────────────────────────

class GetUserPreferenceInput(BaseModel):
    distinct_id: str = Field(
        description="The unique identifier of the user."
    )
    category: str = Field(
        default="",
        description=(
            "Category slug to fetch preference for a single category. "
            "Leave empty to fetch full preferences across all categories."
        ),
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )
    tenant_id: str = Field(
        default="",
        description="Tenant ID to scope preferences. Uses configured default if omitted.",
    )


class GetUserPreferenceTool(SuprSendTool):
    """
    Full preferences:
        GET {base_url}/v1/user/{distinct_id}/preference/?tenant_id=...
        Returns sections (categories + channels) and global channel preferences.

    Single category:
        GET {base_url}/v1/user/{distinct_id}/preference/category/{category}/?tenant_id=...
        Returns preference, opt-out channels, editability for that category.
    """

    name = "get_user_preference"
    description = (
        "Get notification preferences for a user. "
        "Omit category to get all preferences across every notification category. "
        "Pass a category slug to get preferences for that specific category only."
    )
    args_schema = GetUserPreferenceInput
    permission_category = "subscribers"
    permission_operation = "read"

    async def execute(
        self,
        client: AsyncSuprSendClient,
        distinct_id: str = "",
        category: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        tenant = self._tenant_id(client, kwargs)

        if not ws:
            return "Error: workspace is required."
        if not distinct_id:
            return "Error: distinct_id is required."

        try:
            user_path = f"v1/user/{quote(distinct_id, safe='')}/"
            params = {"tenant_id": tenant} if tenant else {}

            if category:
                path = f"{user_path}preference/category/{quote(category, safe='')}/"
            else:
                path = f"{user_path}preference/"

            result = await client.workspace_get(ws, path, params=params)
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error fetching preferences for user '{distinct_id}': {e}"

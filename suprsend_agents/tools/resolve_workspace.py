from pydantic import BaseModel, Field

from suprsend_agents.client import AsyncSuprSendClient
from suprsend_agents.core.base import SuprSendTool


class ResolveWorkspaceInput(BaseModel):
    workspace: str = Field(
        default="",
        description=(
            "The workspace slug to resolve credentials for. "
            "Leave empty to use the default workspace from context."
        ),
    )


class ResolveWorkspaceTool(SuprSendTool):
    """
    Exchanges the current service token (or JWT) for workspace-level
    credentials via: GET /v1/{workspace}/ws_key/bridge

    MUST be called before any workspace-level operation (trigger workflow,
    get/edit user, track event, etc.).  The toolkit always prepends this
    tool to every list so it is always available.

    After a successful call the credentials are cached on the client —
    subsequent workspace tools trigger no extra network call.
    Calling this again for the same workspace is a no-op (served from cache).
    """

    name = "resolve_workspace"
    description = (
        "Exchange the current auth token for workspace credentials. "
        "Always call this FIRST before any other workspace-level tool "
        "(trigger_workflow, get_user, track_event, etc.). "
        "Once called the credentials are cached for the session."
    )
    args_schema = ResolveWorkspaceInput

    async def execute(
        self,
        client: AsyncSuprSendClient,
        workspace: str = "",
        **_: object,
    ) -> str:
        ws = self._workspace(client, {"workspace": workspace})
        if not ws:
            return (
                "Error: workspace is required. "
                "Pass it as an argument or set ToolContext.workspace."
            )

        try:
            key, _ = await client.exchange_workspace_credentials(ws)
            return (
                f"Workspace '{ws}' resolved. "
                f"Key prefix: {key[:8]}… "
                f"You can now call workspace-level tools."
            )
        except Exception as exc:
            return f"Error resolving workspace '{ws}': {exc}"

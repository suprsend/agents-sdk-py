from collections.abc import Callable
from typing import Any
from suprsend_agents_toolkit.auth import ServiceTokenAuth, JWTAuth
from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.context import ToolContext
from suprsend_agents_toolkit.types import Permissions
from suprsend_agents_toolkit.tools.resolve_workspace import ResolveWorkspaceTool
from suprsend_agents_toolkit.tools.search_docs import SearchDocsTool
from suprsend_agents_toolkit.tools.users import (
    GetUserTool,
    GetUserPreferenceTool,
    GetUserObjectSubscriptionsTool,
    GetUserListSubscriptionsTool,
)
from suprsend_agents_toolkit.tools.objects import GetObjectTool, GetObjectPreferenceTool, GetObjectSubscriptionsTool
from suprsend_agents_toolkit.tools.tenants import GetTenantTool, GetTenantPreferenceTool
from suprsend_agents_toolkit.tools.management import GetPreferenceCategoriesTool, ListWorkflowsTool, GetWorkflowTool, PushWorkflowTool, CommitWorkflowTool, GetEventDetailsTool, GetTranslationDetailsTool
from suprsend_agents_toolkit.tools.workflow_trigger import TriggerWorkflowTool
from suprsend_agents_toolkit.tools.event_trigger import TrackEventTool
from suprsend_agents_toolkit.tools.validate_schema import ValidateSchemaTool

__all__ = ["SuprSendToolkit", "ToolContext", "Permissions", "ServiceTokenAuth", "JWTAuth"]

# Tool registry — keyed by tool name.
# resolve_workspace is NOT here; it is always prepended unconditionally.
# Tools with no permission_category (search_docs, guardrail) are always included.
_ALL_TOOLS: dict[str, type] = {
    "search_suprsend_docs": SearchDocsTool,
    # users
    "get_user": GetUserTool,
    "get_user_preference": GetUserPreferenceTool,
    "get_user_object_subscriptions": GetUserObjectSubscriptionsTool,
    "get_user_list_subscriptions": GetUserListSubscriptionsTool,
    # objects
    "get_object": GetObjectTool,
    "get_object_preference": GetObjectPreferenceTool,
    "get_object_subscriptions": GetObjectSubscriptionsTool,
    # tenants
    "get_tenant": GetTenantTool,
    "get_tenant_preference": GetTenantPreferenceTool,
    # management
    "get_preference_categories": GetPreferenceCategoriesTool,
    "list_workflows": ListWorkflowsTool,
    "get_workflow": GetWorkflowTool,
    "push_workflow": PushWorkflowTool,
    "commit_workflow": CommitWorkflowTool,
    "get_event_details": GetEventDetailsTool,
    "get_translation_details": GetTranslationDetailsTool,
    # workflows (trigger)
    "trigger_workflow": TriggerWorkflowTool,
    # events
    "validate_schema": ValidateSchemaTool,
    "track_event": TrackEventTool,
    # coming soon:
    # "guardrail":          GuardrailTool,          no permission (always included)
    # "upsert_subscriber":  UpsertSubscriberTool,   permission_category="subscribers", operation="manage"
}


def _is_permitted(tool_cls: type, permissions: Permissions | None) -> bool:
    """
    Returns True if the tool should be included given the permissions config.

    Rules:
    - No permission_category declared → always included (guardrail, search_docs, etc.)
    - No permissions config on toolkit → all tools included
    - Hub tools: permission_category + operation → check permissions[category][operation]
    - Management tools: permission_category="management", permission_subcategory, operation
      → check permissions["management"][subcategory][operation]
    """
    category = getattr(tool_cls, "permission_category", None)
    subcategory = getattr(tool_cls, "permission_subcategory", None)
    operation = getattr(tool_cls, "permission_operation", None)

    if not category or not operation:
        return True  # no permission gate — always included

    if permissions is None:
        return True  # no restrictions configured — everything allowed

    cat_perms = permissions.get(category, {})
    if subcategory:
        cat_perms = cat_perms.get(subcategory, {})
    return bool(cat_perms.get(operation, False))


class SuprSendToolkit:
    """
    Main entry point.

        toolkit = SuprSendToolkit(
            service_token="sst_...",
            context=ToolContext(workspace="acme", tenant_id="acme-prod"),
            permissions=Permissions(
                workflows={"read": True, "trigger": True},
                subscribers={"read": True, "manage": True},
            ),
        )

        # LangChain / LangGraph
        # resolve_workspace is always first; only permitted tools follow
        tools = toolkit.get_langchain_tools()

        # OpenAI / Anthropic
        tool_defs = toolkit.get_openai_tools()

    Args:
        service_token:  Service token from the SuprSend dashboard.
        context:        ToolContext — workspace slug, URLs, tenant default.
                        Stored on the client; tools access it via client.context.
        permissions:    Which tool categories and operations to expose.
                        When omitted, all registered tools are included.
        auth:           Override with a concrete auth object (e.g. JWTAuth) instead
                        of a service token.
        jwt_getter:     Callable[[run_config], str] called at tool invocation time.
                        Receives the run config and returns the JWT string (or
                        "" to fall back to service token). The host application owns
                        all framework-specific extraction logic (ContextVar, LangGraph
                        auth context, etc.). When combined with service_token, service
                        token is the fallback if jwt_getter returns empty.
    """

    def __init__(
        self,
        service_token: str | None = None,
        context: ToolContext | None = None,
        permissions: Permissions | None = None,
        auth: ServiceTokenAuth | JWTAuth | None = None,
        jwt_getter: "Callable[[Any], str] | None" = None,
    ) -> None:
        if auth:
            _auth = auth
        elif service_token:
            _auth = ServiceTokenAuth(service_token)
        elif jwt_getter:
            _auth = None  # auth resolved per-call via jwt_getter
        else:
            raise ValueError("Provide service_token=, auth=, or jwt_getter=.")

        _ctx = context or ToolContext()
        self._client = AsyncSuprSendClient(auth=_auth, context=_ctx, jwt_getter=jwt_getter)
        self._permissions = permissions

    def _permitted_names(self, requested: list[str] | None) -> list[str]:
        """Names from the requested list (or all) that pass the permission check."""
        names = requested or list(_ALL_TOOLS.keys())
        unknown = [n for n in names if n not in _ALL_TOOLS]
        if unknown:
            raise ValueError(
                f"Unknown tool name(s): {unknown}. "
                f"Valid names: {sorted(_ALL_TOOLS.keys())}"
            )
        return [
            n for n in names
            if _is_permitted(_ALL_TOOLS[n], self._permissions)
        ]

    def _instantiate(self, name: str) -> object:
        return _ALL_TOOLS[name](client=self._client)

    def get_langchain_tools(self, tools: list[str] | None = None) -> list:
        """
        LangChain BaseTool list.
        resolve_workspace is always first.
        All other tools are filtered by the permissions config.
        """
        instances = [ResolveWorkspaceTool(client=self._client)] + [
            self._instantiate(n) for n in self._permitted_names(tools)
        ]
        return [t.to_langchain() for t in instances]

    def get_openai_tools(self, tools: list[str] | None = None) -> list:
        """OpenAI / Anthropic function-calling dicts."""
        instances = [ResolveWorkspaceTool(client=self._client)] + [
            self._instantiate(n) for n in self._permitted_names(tools)
        ]
        return [t.to_openai() for t in instances]

    async def run_tool(self, name: str, args: dict, run_config: Any = None) -> str:
        """
        Execute a tool by name with the given args.

        Intended for use alongside get_openai_tools() — call this from your
        tool dispatch loop when the model returns a tool_call:

            tool_defs = toolkit.get_openai_tools()
            # ... send to OpenAI, receive tool_call ...
            result = await toolkit.run_tool(tool_call.function.name,
                                            json.loads(tool_call.function.arguments))

        Args:
            name:       Tool name as returned in the function-calling response.
            args:       Parsed arguments dict from the model's tool call.
            run_config: Optional framework run config (e.g. LangGraph RunnableConfig)
                        used to extract a per-request JWT when jwt_getter is set.
                        Pass None when using service token auth.

        Returns:
            The tool's string output, ready to send back to the model.

        Raises:
            ValueError: if name is not a registered tool.
        """
        if name == ResolveWorkspaceTool.name:
            instance = ResolveWorkspaceTool(client=self._client)
        elif name in _ALL_TOOLS:
            instance = self._instantiate(name)
        else:
            valid = ["resolve_workspace"] + sorted(_ALL_TOOLS.keys())
            raise ValueError(f"Unknown tool: {name!r}. Valid names: {valid}")
        client = instance._resolve_client(run_config)
        return await instance.execute(client=client, **args)

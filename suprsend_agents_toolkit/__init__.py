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
    CreateUserTool,
    UpdateUserTool,
    UpdateUserPreferenceCategoryTool,
    UpdateUserPreferenceChannelTool,
)
from suprsend_agents_toolkit.tools.objects import (
    GetObjectTool,
    GetObjectPreferenceTool,
    GetObjectSubscriptionsTool,
    CreateObjectTool,
    UpdateObjectTool,
    AddObjectSubscriptionTool,
    UpdateObjectPreferenceCategoryTool,
    UpdateObjectPreferenceChannelTool,
)
from suprsend_agents_toolkit.tools.tenants import (
    GetTenantTool,
    GetTenantPreferenceTool,
    UpsertTenantTool,
    UpdateTenantPreferenceCategoryTool,
)
from suprsend_agents_toolkit.tools.management import (
    GetPreferenceCategoriesTool,
    UpdatePreferenceCategoryTool,
    ListWorkflowsTool,
    GetWorkflowTool,
    ValidateWorkflowTool,
    PushWorkflowTool,
    CommitWorkflowTool,
    GetEventDetailsTool,
    GetTranslationDetailsTool,
    UpdateTranslationTool,
    CommitTranslationTool,
    ListSchemasTool,
    GetSchemaTool,
    PushSchemaTool,
    CommitSchemaTool,
    LinkEventSchemaTool,
)
from suprsend_agents_toolkit.tools.lists import AddUserToListTool, RemoveUserFromListTool
from suprsend_agents_toolkit.tools.workflow_trigger import TriggerWorkflowTool
from suprsend_agents_toolkit.tools.event_trigger import TrackEventTool
from suprsend_agents_toolkit.tools.validate_schema import ValidateSchemaTool

__all__ = ["SuprSendToolkit", "ToolContext", "Permissions", "ServiceTokenAuth", "JWTAuth"]

# Tools that are always included and always come first — not subject to
# permission filtering and not selectable via the tools= argument.
_BUILTIN_TOOLS: dict[str, type] = {
    ResolveWorkspaceTool.name: ResolveWorkspaceTool,
}

# Tool registry — keyed by tool name.
# Tools with no permission_category (search_docs) are always included.
_ALL_TOOLS: dict[str, type] = {
    "search_suprsend_docs": SearchDocsTool,
    # users
    "get_user": GetUserTool,
    "get_user_preference": GetUserPreferenceTool,
    "get_user_object_subscriptions": GetUserObjectSubscriptionsTool,
    "get_user_list_subscriptions": GetUserListSubscriptionsTool,
    "create_user": CreateUserTool,
    "update_user": UpdateUserTool,
    "update_user_preference_category": UpdateUserPreferenceCategoryTool,
    "update_user_preference_channel": UpdateUserPreferenceChannelTool,
    # objects
    "get_object": GetObjectTool,
    "get_object_preference": GetObjectPreferenceTool,
    "get_object_subscriptions": GetObjectSubscriptionsTool,
    "create_object": CreateObjectTool,
    "update_object": UpdateObjectTool,
    "add_object_subscription": AddObjectSubscriptionTool,
    "update_object_preference_category": UpdateObjectPreferenceCategoryTool,
    "update_object_preference_channel": UpdateObjectPreferenceChannelTool,
    # tenants
    "get_tenant": GetTenantTool,
    "get_tenant_preference": GetTenantPreferenceTool,
    "upsert_tenant": UpsertTenantTool,
    "update_tenant_preference_category": UpdateTenantPreferenceCategoryTool,
    # management
    "get_preference_categories": GetPreferenceCategoriesTool,
    "update_preference_category": UpdatePreferenceCategoryTool,
    "list_workflows": ListWorkflowsTool,
    "get_workflow": GetWorkflowTool,
    "validate_workflow": ValidateWorkflowTool,
    "push_workflow": PushWorkflowTool,
    "commit_workflow": CommitWorkflowTool,
    "get_event_details": GetEventDetailsTool,
    "get_translation_details": GetTranslationDetailsTool,
    "update_translation": UpdateTranslationTool,
    "commit_translation": CommitTranslationTool,
    "list_schemas": ListSchemasTool,
    "get_schema": GetSchemaTool,
    "push_schema": PushSchemaTool,
    "commit_schema": CommitSchemaTool,
    "link_event_schema": LinkEventSchemaTool,
    # lists
    "add_user_to_list": AddUserToListTool,
    "remove_user_from_list": RemoveUserFromListTool,
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
        service_token:    Service token from the SuprSend dashboard.
        context:          ToolContext — workspace slug, URLs, tenant default.
                          Stored on the client; tools access it via client.context.
        permissions:      Which tool categories and operations to expose.
                          When omitted, all registered tools are included.
        auth:             Override with a concrete auth object (e.g. JWTAuth) instead
                          of a service token.
        jwt_getter:       Callable[[run_config], str] called at tool invocation time.
                          Receives the run config and returns the JWT string (or
                          "" to fall back to service token). The host application owns
                          all framework-specific extraction logic (ContextVar, LangGraph
                          auth context, etc.). When combined with service_token, service
                          token is the fallback if jwt_getter returns empty.
        allow_writes:     When False, any tool with read_only=False raises PermissionError
                          before executing. Use this to create a strictly read-only agent.
                          Default: True.
        allow_destructive: When False, any tool with destructive=True raises PermissionError
                          before executing. Use this to prevent the agent from taking
                          irreversible actions even when writes are otherwise permitted.
                          Default: True.
    """

    def __init__(
        self,
        service_token: str | None = None,
        context: ToolContext | None = None,
        permissions: Permissions | None = None,
        auth: ServiceTokenAuth | JWTAuth | None = None,
        jwt_getter: "Callable[[Any], str] | None" = None,
        allow_writes: bool = True,
        allow_destructive: bool = True,
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
        _policy = {"allow_writes": allow_writes, "allow_destructive": allow_destructive}
        self._client = AsyncSuprSendClient(auth=_auth, context=_ctx, jwt_getter=jwt_getter, policy=_policy)
        self._permissions = permissions

    def _permitted_names(self, requested: list[str] | None) -> list[str]:
        """Names from the requested list (or all) that pass the permission check."""
        names = requested or list(_ALL_TOOLS.keys())
        _known = _ALL_TOOLS.keys() | _BUILTIN_TOOLS.keys()
        unknown = [n for n in names if n not in _known]
        if unknown:
            raise ValueError(
                f"Unknown tool name(s): {unknown}. "
                f"Valid names: {sorted(_known)}"
            )
        return [
            n for n in names
            if _is_permitted(_ALL_TOOLS[n], self._permissions)
        ]

    def _instantiate(self, name: str) -> object:
        return _ALL_TOOLS[name](client=self._client)

    def _builtin_instances(self) -> list:
        return [cls(client=self._client) for cls in _BUILTIN_TOOLS.values()]

    def get_langchain_tools(self, tools: list[str] | None = None) -> list:
        """
        LangChain BaseTool list.
        Builtin tools (resolve_workspace) are always first.
        All other tools are filtered by the permissions config.
        """
        instances = self._builtin_instances() + [
            self._instantiate(n) for n in self._permitted_names(tools)
        ]
        return [t.to_langchain() for t in instances]

    def get_openai_tools(self, tools: list[str] | None = None) -> list:
        """OpenAI / Anthropic function-calling dicts."""
        instances = self._builtin_instances() + [
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
            ValueError: if name is not a registered tool or is not permitted.
        """
        if name in _BUILTIN_TOOLS:
            instance = _BUILTIN_TOOLS[name](client=self._client)
        elif name in _ALL_TOOLS:
            if not _is_permitted(_ALL_TOOLS[name], self._permissions):
                raise ValueError(f"Tool {name!r} is not permitted by the current permissions config.")
            instance = self._instantiate(name)
        else:
            valid = sorted(_BUILTIN_TOOLS.keys()) + sorted(_ALL_TOOLS.keys())
            raise ValueError(f"Unknown tool: {name!r}. Valid names: {valid}")
        client = instance._resolve_client(run_config)
        instance._enforce_policy(client)
        return await instance.execute(client=client, **args)

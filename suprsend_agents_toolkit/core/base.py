from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

try:
    from langchain_core.runnables import RunnableConfig
except ImportError:
    RunnableConfig = Any  # type: ignore[assignment,misc]


class SuprSendTool(ABC):
    """
    Abstract base for every SuprSend tool.

    Subclasses define:
        name                  — unique tool identifier (snake_case)
        description           — shown to the LLM
        args_schema           — Pydantic model; LLM-visible input schema
        permission_category   — e.g. "workflows", "subscribers", "tenants"
        permission_operation  — "read" or "manage"

    Tools without permission_category / permission_operation are always
    included (e.g. resolve_workspace, guardrail, search_docs).

    And implement:
        execute(client, **kwargs) → str

    ── Context fallback pattern (mirrors Knock's agent-toolkit) ─────────────
    Schema fields for workspace and tenant_id are always *optional*.
    The LLM supplies them when it knows them from the conversation; when
    it omits them the tool falls back to the values configured on the client.

    Every tool that needs a workspace or tenant should resolve them via the
    two helpers rather than reading kwargs directly:

        ws     = self._workspace(client, kwargs)
        tenant = self._tenant_id(client, kwargs)

    Helper logic:
        workspace  → kwargs["workspace"]  or  client.context.workspace
        tenant_id  → kwargs["tenant_id"]  or  client.context.tenant_id  or  "default"

    ── JWT override (copilot) ────────────────────────────────────────────────
    _resolve_client() swaps ServiceTokenAuth → JWTAuth at call time by
    calling jwt_getter(config). The host application provides the callable
    and owns all framework-specific extraction logic.
    """

    name: str
    description: str
    args_schema: type[BaseModel]
    permission_category: str | None = None   # "workflows" | "subscribers" | ...
    permission_operation: str | None = None  # "read" | "manage" | "trigger"

    # Annotations — describe the tool's behaviour characteristics
    read_only: bool = True    # does not mutate any state
    destructive: bool = False # can permanently delete or overwrite data
    idempotent: bool = True   # repeated identical calls produce the same result
    open_world: bool = True   # may return data that changes between calls

    def __init__(self, client: Any) -> None:
        self._client = client  # AsyncSuprSendClient

    # ── Context helpers ───────────────────────────────────────────────────────

    def _workspace(self, client: Any, kwargs: dict) -> str:
        """
        Resolve workspace: context default first, then explicit kwarg.
        If context.workspace is set it always wins — tools are scoped to that
        workspace regardless of what the LLM or thread metadata supplies.
        Falls back to the kwarg when context is not configured.
        """
        return client.context.workspace or kwargs.get("workspace")

    def _tenant_id(self, client: Any, kwargs: dict) -> str:
        """
        Resolve tenant_id: explicit kwarg first, then context default,
        then "default" as the final fallback (SuprSend's built-in tenant).
        """
        return kwargs.get("tenant_id") or client.context.tenant_id or "default"

    # ── Auth resolution ───────────────────────────────────────────────────────

    def _resolve_client(self, run_config: Any) -> Any:
        """
        Return the right HTTP client for this specific tool invocation.

        If the toolkit was constructed with jwt_getter, call it now with the
        current run config. The callable is fully owned by the host
        application — it can read from a ContextVar, LangGraph's auth context,
        or any other request-scoped source.

        Falls back to the construction-time auth (service token) if no JWT.
        """
        if self._client.jwt_getter:
            jwt_token = self._client.jwt_getter(run_config)
            if jwt_token:
                return self._client._with_jwt(jwt_token)
        return self._client

    # ── Core logic (subclasses implement) ─────────────────────────────────────

    @abstractmethod
    async def execute(self, client: Any, **kwargs: Any) -> str:
        """
        Tool logic. Resolve workspace / tenant via the helpers:

            ws     = self._workspace(client, kwargs)
            tenant = self._tenant_id(client, kwargs)

        Use client.workspace_post / client.workspace_get for hub API calls.
        Use client.mgmnt_get / client.mgmnt_post for management API calls.
        """
        ...

    # ── Adapters ──────────────────────────────────────────────────────────────

    def to_langchain(self) -> Any:
        """
        Return a LangChain StructuredTool.
        run_config: RunnableConfig is injected by LangGraph at every call,
        enabling the JWT swap without changes in execute().
        """
        from langchain_core.tools import StructuredTool

        tool_self = self

        async def _run(run_config: RunnableConfig, **kwargs: Any) -> str:
            client = tool_self._resolve_client(run_config)
            return await tool_self.execute(client=client, **kwargs)

        return StructuredTool.from_function(
            coroutine=_run,
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
            handle_tool_error=True,
        )

    def to_openai(self) -> dict:
        """OpenAI / Anthropic function-calling dict."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema(),
            },
        }

# suprsend-agents

Python SDK for building AI agents that interact with [SuprSend](https://suprsend.com) — the notification infrastructure platform.

Exposes SuprSend API operations as agent-ready tools for LangChain, LangGraph, and OpenAI function calling.

## Installation

```bash
pip install suprsend-agents
```

**With LangChain / LangGraph support:**
```bash
pip install "suprsend-agents[langchain]"
```

**Local development (editable install):**
```bash
pip install -e ./agents-sdk-py
```

## Quick Start

```python
from suprsend_agents import SuprSendToolkit, ToolContext

toolkit = SuprSendToolkit(
    service_token="sst_...",
    context=ToolContext(workspace="your-workspace"),
)

# LangChain / LangGraph
tools = toolkit.get_langchain_tools()

# OpenAI / Anthropic function calling
tool_defs = toolkit.get_openai_tools()
```

## Authentication

Two auth strategies are supported:

### Service Token (default)

For server-side agents and Slack bots. Issued from the SuprSend dashboard.

```python
toolkit = SuprSendToolkit(service_token="sst_...")
```

### JWT (per-user)

For user-facing agents (e.g. embedded copilots) where each request is scoped to an authenticated user.

**Inside LangGraph** — pass a `jwt_getter` callable. LangGraph injects the `RunnableConfig` at every tool call; the callable extracts the JWT from it. The host application owns all framework-specific extraction logic.

```python
def get_jwt(run_config) -> str:
    try:
        configurable = (run_config or {}).get("configurable") or {}
        auth_user = configurable.get("langgraph_auth_user")
        if auth_user:
            return auth_user.get("jwt_token") or ""
    except (KeyError, TypeError):
        pass
    return ""

toolkit = SuprSendToolkit(
    jwt_getter=get_jwt,
    context=ToolContext(workspace="your-workspace"),
)
```

**Outside LangGraph** — construct `JWTAuth` directly:

```python
from suprsend_agents import JWTAuth

auth = JWTAuth.from_header(request.headers["Authorization"])
auth = JWTAuth.from_cookie(request.headers["cookie"], cookie_name="my-auth-token")
auth = JWTAuth.from_request(
    authorization_header=request.headers.get("authorization"),
    cookie_header=request.headers.get("cookie"),
    cookie_name="my-auth-token",
)

toolkit = SuprSendToolkit(auth=auth, context=ToolContext(workspace="your-workspace"))
```

## ToolContext

`ToolContext` holds workspace-level defaults passed to every tool:

```python
from suprsend_agents import ToolContext

context = ToolContext(
    workspace="your-workspace",       # workspace slug (required for most tools)
    base_url="https://hub.suprsend.com",
    mgmnt_url="https://management-api.suprsend.com",
    tenant_id="acme-prod",            # default tenant (tools can override per-call)
    dashboard_url="https://app.suprsend.com",
)
```

## Available Tools

`resolve_workspace` is always prepended to every tool list — it exchanges the auth token for workspace credentials and caches the result.

| Tool | Description | Permission |
|------|-------------|------------|
| `resolve_workspace` | Exchange token for workspace credentials (always first) | — |
| `search_suprsend_docs` | Search SuprSend documentation | — |
| `get_user` | Get user profile and channel identities | `subscribers.read` |
| `get_user_preference` | Get notification preferences for a user | `subscribers.read` |
| `get_object` | Get object profile and channel identities | `subscribers.read` |
| `get_object_preference` | Get notification preferences for an object | `subscribers.read` |
| `get_object_subscriptions` | List subscribers for an object | `subscribers.read` |
| `get_tenant` | Get tenant profile, branding, and settings | `tenants.read` |
| `get_tenant_preference` | Get all notification category preferences for a tenant | `tenants.read` |

### Selecting Tools

```python
# All tools
tools = toolkit.get_langchain_tools()

# Subset
tools = toolkit.get_langchain_tools(["search_suprsend_docs", "get_user"])
```

### Permissions

Restrict which tools are exposed using the `Permissions` config:

```python
from suprsend_agents import SuprSendToolkit, Permissions

toolkit = SuprSendToolkit(
    service_token="sst_...",
    context=context,
    permissions=Permissions(
        subscribers={"read": True},
        tenants={"read": True},
    ),
)
```

Tools without a `permission_category` (e.g. `search_suprsend_docs`) are always included regardless of the permissions config.

## LangGraph Example

```python
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from suprsend_agents import SuprSendToolkit, ToolContext

toolkit = SuprSendToolkit(
    service_token="sst_...",
    context=ToolContext(workspace="your-workspace"),
)

agent = create_react_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    tools=toolkit.get_langchain_tools(),
)
```

## Injecting Context at Tool Call Time

Tools expose all their parameters (workspace, tenant_id, etc.) as optional fields so the LLM can supply them when known. For server-side use you typically have this context already — from a session, a database record, or request metadata — and want to inject it automatically rather than relying on the LLM.

A common example is **workspace injection**: the workspace slug is known at request time and should flow into every tool call without the LLM having to supply it.

### LangGraph

LangGraph injects a `RunnableConfig` into every tool call. Wrap the tool to read context from `run_config.configurable` (where LangGraph surfaces thread metadata and auth state):

```python
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableConfig

def inject_workspace(lc_tool) -> StructuredTool:
    original = lc_tool.coroutine

    async def _run(run_config: RunnableConfig, **kwargs) -> str:
        if not kwargs.get("workspace"):
            configurable = (run_config or {}).get("configurable") or {}
            ws = configurable.get("workspace_slug", "")
            if ws:
                kwargs["workspace"] = ws
        return await original(run_config=run_config, **kwargs)

    return StructuredTool.from_function(
        coroutine=_run,
        name=lc_tool.name,
        description=lc_tool.description,
        args_schema=lc_tool.args_schema,
    )

tools = [inject_workspace(t) for t in toolkit.get_langchain_tools([...])]
```

### OpenAI / Anthropic function calling

There is no `RunnableConfig` here. Use a **closure** to capture the workspace at the point where you handle the tool call:

```python
tool_defs = toolkit.get_openai_tools()

async def handle_tool_call(name: str, args: dict, workspace: str) -> str:
    # Inject workspace before dispatching — args come from the model's JSON output
    args.setdefault("workspace", workspace)
    return await toolkit.call(name, args)
```

Or bind it at construction time via `ToolContext` if the workspace is the same for every request from a given tenant:

```python
toolkit = SuprSendToolkit(
    service_token="sst_...",
    context=ToolContext(workspace="acme"),   # applied to every tool call
)
```

### Python ContextVar (any framework)

For frameworks that do not pass a request object into tool execution, a `ContextVar` lets you set context once per request and read it anywhere in the same async task:

```python
from contextvars import ContextVar

_workspace_ctx: ContextVar[str] = ContextVar("workspace", default="")

# In your request handler, before invoking the agent:
_workspace_ctx.set(current_user.workspace_slug)

# In a thin wrapper around the tool:
async def _run(**kwargs) -> str:
    kwargs.setdefault("workspace", _workspace_ctx.get())
    return await original_tool(**kwargs)
```

The same pattern applies to any per-request value — tenant ID, locale, or feature flags.

## Adding Custom Tools

Subclass `SuprSendTool` and register it with your toolkit:

```python
from pydantic import BaseModel, Field
from suprsend_agents.core.base import SuprSendTool

class MyInput(BaseModel):
    workspace: str = Field(default="")

class MyTool(SuprSendTool):
    name = "my_tool"
    description = "Does something useful."
    args_schema = MyInput
    permission_category = "workflows"   # optional — omit to always include
    permission_operation = "read"

    async def execute(self, client, **kwargs) -> str:
        ws = self._workspace(client, kwargs)
        result = await client.mgmnt_get(f"v1/{ws}/workflows/")
        return str(result)
```

## Requirements

- Python 3.11+
- `aiohttp>=3.9`
- `pydantic>=2.0`
- `langchain-core>=0.3` (optional, for LangChain/LangGraph integration)
- `mcp>=1.0` (optional, for `search_suprsend_docs`)

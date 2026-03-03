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

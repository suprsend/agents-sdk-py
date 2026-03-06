# suprsend-agents-toolkit

Python SDK for building AI agents that interact with [SuprSend](https://suprsend.com) — the notification infrastructure platform.

Exposes SuprSend API operations as agent-ready tools for LangChain, LangGraph, and OpenAI function calling.

## Installation

**pip**
```bash
pip install suprsend-agents-toolkit
```

**uv**
```bash
uv add suprsend-agents-toolkit
```

**With LangChain / LangGraph support:**
```bash
# pip
pip install "suprsend-agents-toolkit[langchain]"

# uv
uv add "suprsend-agents-toolkit[langchain]"
```

## Quick Start

```python
from suprsend_agents_toolkit import SuprSendToolkit, ToolContext

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

Service tokens are issued from the SuprSend dashboard and used for server-side agents.

```python
toolkit = SuprSendToolkit(service_token="sst_...")
```

## ToolContext

`ToolContext` holds workspace-level defaults passed to every tool:

```python
from suprsend_agents_toolkit import ToolContext

context = ToolContext(
    workspace="your-workspace",    # required for most tools
    tenant_id="acme-prod",         # optional — default tenant, tools can override per-call
)
```

## Available Tools

**Hub tools** (hit `hub.suprsend.com` via HMAC-signed SDK):

| Tool | Description | Permission |
|------|-------------|------------|
| `search_suprsend_docs` | Search SuprSend documentation | — |
| `get_user` | Get user profile and channel identities | `subscribers.read` |
| `get_user_preference` | Get notification preferences for a user | `subscribers.read` |
| `get_user_object_subscriptions` | List objects a user is subscribed to | `subscribers.read` |
| `get_user_list_subscriptions` | List broadcast lists a user belongs to | `subscribers.read` |
| `get_object` | Get object profile and channel identities | `subscribers.read` |
| `get_object_preference` | Get notification preferences for an object | `subscribers.read` |
| `get_object_subscriptions` | List subscribers for an object | `subscribers.read` |
| `get_tenant` | Get tenant profile, branding, and settings | `tenants.read` |
| `get_tenant_preference` | Get all notification category preferences for a tenant | `tenants.read` |

**Management tools** (hit `management-api.suprsend.com`, require `api_secret` on `ToolContext`):

| Tool | Description | Permission |
|------|-------------|------------|
| `get_preference_categories` | List all notification preference categories in the workspace | `management.preference_categories.read` |
| `list_workflows` | List workflows with optional search, slug filter, and sort | `management.workflows.read` |
| `get_workflow` | Fetch full details of a single workflow by slug | `management.workflows.read` |

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
from suprsend_agents_toolkit import SuprSendToolkit, Permissions

toolkit = SuprSendToolkit(
    service_token="sst_...",
    context=context,
    permissions=Permissions(
        subscribers={"read": True},
        tenants={"read": True},
        management={"workflows": {"read": True}, "preference_categories": {"read": True}},
    ),
)
```

Tools without a `permission_category` (e.g. `search_suprsend_docs`) are always included regardless of the permissions config.

## LangGraph Example

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from suprsend_agents_toolkit import SuprSendToolkit, ToolContext

toolkit = SuprSendToolkit(
    service_token="sst_...",
    context=ToolContext(workspace="your-workspace"),
)

agent = create_agent(
    model=ChatAnthropic(model="claude-sonnet-4-6"),
    tools=toolkit.get_langchain_tools(),
)
```

## Requirements

- Python 3.11+
- `aiohttp>=3.9`
- `pydantic>=2.0`
- `langchain-core>=0.3` (optional, for LangChain/LangGraph integration)
- `mcp>=1.0` (optional, for `search_suprsend_docs`)
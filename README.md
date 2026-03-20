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

Service tokens are issued from the SuprSend dashboard and used for server-side agents:

```python
toolkit = SuprSendToolkit(service_token="sst_...")
```

## ToolContext

`ToolContext` holds workspace-level defaults passed to every tool:

```python
from suprsend_agents_toolkit import ToolContext

context = ToolContext(
    workspace="your-workspace",    # default workspace slug; tools can override per-call
    tenant_id="acme-prod",         # optional default tenant
)
```

## Available Tools

### Hub tools

Hit `hub.suprsend.com` via HMAC-signed SDK credentials.

**Subscribers (read)**

| Tool | Description | Permission |
|------|-------------|------------|
| `get_user` | Fetch a user's full profile, channel addresses, and custom properties | `subscribers.read` |
| `get_user_preference` | Get notification preferences for a user (full or single category) | `subscribers.read` |
| `get_user_object_subscriptions` | List objects a user is subscribed to | `subscribers.read` |
| `get_user_list_subscriptions` | List broadcast lists a user belongs to | `subscribers.read` |
| `get_object` | Fetch an object's full profile, channel addresses, and custom properties | `subscribers.read` |
| `get_object_preference` | Get notification preferences for an object | `subscribers.read` |
| `get_object_subscriptions` | List subscribers (users or child objects) for an object | `subscribers.read` |

**Subscribers (write)**

| Tool | Description | Permission |
|------|-------------|------------|
| `create_user` | Create or replace a user profile (upsert) | `subscribers.manage` |
| `update_user` | Apply partial updates to a user via operations (`$set`, `$unset`, `$add_email`, etc.) | `subscribers.manage` |
| `create_object` | Create or replace an object profile (upsert) | `subscribers.manage` |
| `update_object` | Apply partial updates to an object via operations | `subscribers.manage` |
| `add_object_subscription` | Add subscribers (users or child objects) to an object | `subscribers.manage` |

**Tenants (read)**

| Tool | Description | Permission |
|------|-------------|------------|
| `get_tenant` | Fetch tenant profile, branding, and settings | `tenants.read` |
| `get_tenant_preference` | List all notification category preferences for a tenant | `tenants.read` |

**Tenants (write)**

| Tool | Description | Permission |
|------|-------------|------------|
| `upsert_tenant` | Create or update a tenant's branding, channels, and custom properties | `tenants.manage` |

**Workflows (trigger)**

| Tool | Description | Permission |
|------|-------------|------------|
| `trigger_workflow` | Trigger a published workflow for one or more recipients | `workflows.trigger` |

**Events**

| Tool | Description | Permission |
|------|-------------|------------|
| `track_event` | Track a named event for a user | `events.trigger` |
| `validate_schema` | Validate an event payload against its registered schema | `events.read` |

---

### Management tools

Hit `management-api.suprsend.com`. Require `api_secret` on `ToolContext`. Auth is via ServiceToken or JWT Bearer + `x-ss-api-secret` header.

**Preference categories**

| Tool | Description | Permission |
|------|-------------|------------|
| `get_preference_categories` | List all notification preference categories in the workspace | `management.preference_categories.read` |
| `update_preference_category` | Update display name, description, default opt-in/out, and mandatory channels for a category | `management.preference_categories.manage` |

**Workflows**

| Tool | Description | Permission |
|------|-------------|------------|
| `list_workflows` | List workflows with optional search, slug filter, and sort | `management.workflows.read` |
| `get_workflow` | Fetch full details of a single workflow by slug | `management.workflows.read` |
| `push_workflow` | Push a workflow definition as a draft (optionally deploy immediately) | `management.workflows.manage` |
| `commit_workflow` | Deploy a saved workflow draft to production | `management.workflows.manage` |

**Events**

| Tool | Description | Permission |
|------|-------------|------------|
| `get_event_details` | Fetch schema and metadata for a registered event | `management.events.read` |

**Translations**

| Tool | Description | Permission |
|------|-------------|------------|
| `get_translation_details` | Fetch the content of a translation file by filename | `management.translations.read` |
| `update_translation` | Create or update a translation file with key-value string pairs | `management.translations.manage` |

---

### Always-included tools

| Tool | Description |
|------|-------------|
| `search_suprsend_docs` | Semantic search over SuprSend documentation |

---

## Write Operations

### User / Object update operations

`update_user` and `update_object` accept an `operations` list. Each entry is one operation dict:

```python
operations = [
    {"$set": {"name": "Alice", "plan": "enterprise"}},
    {"$add_email": "alice@example.com"},
    {"$remove_sms": "+1234567890"},
    {"$unset": ["legacy_field"]},
]
```

### Upsert payload (create_user / create_object)

Pass channel addresses and custom properties directly:

```python
properties = {
    "$name": "Alice",
    "$email": "alice@example.com",
    "$sms": "+1234567890",
    "custom_prop": "value",
}
```

### Object subscriptions

`add_object_subscription` recipients can be user distinct_id strings or object reference dicts:

```python
recipients = [
    "user_distinct_id",
    {"object_type": "teams", "id": "team_123"},
]
```

---

## Selecting Tools

```python
# All tools
tools = toolkit.get_langchain_tools()

# Subset by name
tools = toolkit.get_langchain_tools(["get_user", "update_user", "trigger_workflow"])
```

## Permissions

Restrict which tools are exposed using the `Permissions` config:

```python
from suprsend_agents_toolkit import SuprSendToolkit, Permissions

toolkit = SuprSendToolkit(
    service_token="sst_...",
    context=context,
    permissions=Permissions(
        subscribers={"read": True, "manage": True},
        tenants={"read": True, "manage": True},
        workflows={"trigger": True},
        events={"read": True, "trigger": True},
        management={
            "workflows": {"read": True, "manage": True},
            "preference_categories": {"read": True, "manage": True},
            "translations": {"read": True, "manage": True},
            "events": {"read": True},
        },
    ),
)
```

Tools without a `permission_category` (e.g. `search_suprsend_docs`) are always included regardless of the permissions config.

## Write safety flags

```python
toolkit = SuprSendToolkit(
    service_token="sst_...",
    allow_writes=False,       # block all tools with read_only=False
    allow_destructive=False,  # block all tools with destructive=True
)
```

## OpenAI / Anthropic function calling

```python
tool_defs = toolkit.get_openai_tools()

# Dispatch tool calls from the model response
result = await toolkit.run_tool(
    tool_call.function.name,
    json.loads(tool_call.function.arguments),
    run_config=run_config,  # optional — pass when using jwt_getter
)
```

## LangGraph Example

```python
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from suprsend_agents_toolkit import SuprSendToolkit, ToolContext

toolkit = SuprSendToolkit(
    service_token="sst_...",
    context=ToolContext(workspace="your-workspace"),
)

agent = create_react_agent(
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
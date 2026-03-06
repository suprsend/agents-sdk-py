# SuprSend Agent — Terminal Chat Example

Interactive terminal agent that uses `suprsend-agents-toolkit` and LangGraph to answer questions and fetch live data from your SuprSend workspace.

## Setup

**1. Install dependencies**

```bash
# pip
pip install "suprsend-agents-toolkit[langchain]" langchain-anthropic python-dotenv

# uv
uv add "suprsend-agents-toolkit[langchain]" langchain-anthropic python-dotenv
```

**2. Configure environment**

```bash
cp .env.example .env
```

Fill in `.env`:

| Variable | Description |
|----------|-------------|
| `SUPRSEND_SERVICE_TOKEN` | Service token from the SuprSend dashboard |
| `SUPRSEND_WORKSPACE` | Your workspace slug |
| `ANTHROPIC_API_KEY` | Anthropic API key |

**3. Run**

```bash
python examples/langchain/agent.py
```

## Usage

```
SuprSend Agent  (type 'exit' to quit)

You: Get the profile for user alice@example.com
Agent: ...

You: Show me her notification preferences
Agent: ...

You: exit
Goodbye!
```

The agent maintains conversation history across turns, so follow-up questions work naturally.

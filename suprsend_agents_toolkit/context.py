from dataclasses import dataclass, field


@dataclass
class ToolContext:
    """
    Workspace-level defaults. Attached to the client at construction time
    and accessible from every tool via client.context.

    workspace     — slug used in every API path (required for most tools).
    tenant_id     — Default tenant forwarded to tools that accept one.
                    Tools can override per-call; this is just the fallback.
    dashboard_url — Embedded in tool responses as a clickable link.
                    Defaults to https://app.suprsend.com.

    Internal URLs (base_url, mgmnt_url) have sensible defaults and rarely
    need to be changed.
    """

    workspace: str = ""
    tenant_id: str | None = None
    dashboard_url: str = "https://app.suprsend.com"

    # Internal — override only if pointing at a self-hosted or staging instance
    base_url: str = "https://hub.suprsend.com"
    mgmnt_url: str = "https://management-api.suprsend.com"

from dataclasses import dataclass, field


@dataclass
class ToolContext:
    """
    Workspace-level defaults and URLs.  Attached to the client at
    construction time and accessible from every tool via client.context.

    workspace     — slug used in every API path and the exchange call.
    base_url      — SuprSend hub API (workspace-level ops, exchange endpoint).
    mgmnt_url     — Management API (list workflows, schemas, etc.).
    tenant_id     — Default tenant forwarded to tools that accept one.
                    Tools can override per-call; this is just the fallback.
    dashboard_url — Embedded in tool responses as a clickable link.
    docs_url      — Embedded in tool responses as a clickable link.

    Note: distinct_id is intentionally absent — it is a per-user /
    per-call concept, not a workspace-level default.  Pass it explicitly
    when calling tools that require it.

    Example:
        context = ToolContext(
            workspace="acme",
            tenant_id="acme-prod",
            dashboard_url="https://app.suprsend.com",
        )
        toolkit = SuprSendToolkit(service_token="sst_...", context=context)
        # context is stored on client — tools access it via client.context
    """

    workspace: str = ""
    base_url: str = "https://hub.suprsend.com"
    mgmnt_url: str = "https://management-api.suprsend.com"
    tenant_id: str | None = None
    dashboard_url: str | None = None
    docs_url: str = "https://docs.suprsend.com"

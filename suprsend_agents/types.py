from dataclasses import dataclass, field
from typing import Any
from typing_extensions import TypedDict


# ── Permissions ───────────────────────────────────────────────────────────────

class ResourcePermissions(TypedDict, total=False):
    """read = list/get operations.  manage = create/update/delete operations."""
    read: bool
    manage: bool


class WorkflowPermissions(TypedDict, total=False):
    """
    read    — list_workflows, get_workflow
    manage  — create/update workflow definitions
    trigger — trigger_workflow.
              True  → all workflows permitted.
              False / omitted → trigger_workflow excluded.
              (Per-workflow slug filtering is a future addition.)
    """
    read: bool
    manage: bool
    trigger: bool


class Permissions(TypedDict, total=False):
    """
    Passed to SuprSendToolkit at creation time.
    Only tools whose category + operation are enabled are included.
    resolve_workspace, guardrail, and search_docs are always included.

    Example — read-only access to workflows and subscribers:
        Permissions(
            workflows={"read": True},
            subscribers={"read": True},
        )

    Example — full access:
        Permissions(
            workflows={"read": True, "manage": True, "trigger": True},
            subscribers={"read": True, "manage": True},
            events={"manage": True},
            tenants={"read": True},
        )
    """
    workflows: WorkflowPermissions
    subscribers: ResourcePermissions
    events: ResourcePermissions
    tenants: ResourcePermissions


# ── Workspace credentials ─────────────────────────────────────────────────────

@dataclass
class WorkspaceCredentials:
    """
    Workspace key + secret returned by the exchange API.
    Stored in the client's cache after the first resolve_workspace call.
    """

    workspace: str
    key: str
    secret: str


# ── Human-in-the-Loop (future) ────────────────────────────────────────────────

@dataclass
class DeferredToolCall:
    """
    Created when a tool is wrapped with require_human_approval().
    Serialised into the SuprSend approval workflow payload so the
    human can inspect what the agent wants to do before approving.
    """

    id: str                      # uuid — idempotency key for the approval workflow
    method: str                  # tool name, e.g. "trigger_workflow"
    args: dict[str, Any]         # exact kwargs the agent passed
    thread_id: str | None = None # LangGraph thread to resume after approval
    run_id: str | None = None    # LangGraph run to resume


@dataclass
class DeferredToolCallResult:
    """
    Returned by handle_message_interaction() after parsing the
    SuprSend webhook for an approve / reject decision.
    Pass result.approved to decide whether to resume the agent run.
    """

    tool_call_id: str
    approved: bool
    result: str | None = None  # human's optional free-text comment

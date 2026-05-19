import json
from typing import Literal

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool


# ── DraftTriggerWorkflowTool ──────────────────────────────────────────────────

class DraftTriggerWorkflowInput(BaseModel):
    workflow_slug: str = Field(description="Slug of the workflow to test.")
    version_id: str = Field(description="Workflow version ULID to run (from list_workflow_versions).")
    trigger_type: Literal["api", "event"] = Field(description="How the workflow is triggered.")
    data: dict = Field(default_factory=dict, description="Template variable substitution data.")

    # api-triggered
    recipients: list = Field(
        default_factory=list,
        description="Recipients as distinct_id strings or {distinct_id, ...} dicts. Required for trigger_type='api'.",
    )
    actor: str = Field(default="", description="Actor distinct_id (optional, api-triggered only).")

    # event-triggered
    distinct_id: str = Field(default="", description="Recipient distinct_id. Required for trigger_type='event'.")
    event: str = Field(default="", description="Event name. Required for trigger_type='event'.")

    tenant_id: str = Field(default="", description="Tenant ID (optional).")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class DraftTriggerWorkflowTool(ManagementTool):
    """POST {mgmnt_url}/v2/{ws}/workflow/{workflow_slug}/test_run/"""

    name = "draft_trigger_workflow"
    description = (
        "Send a test run for a specific workflow draft version. "
        "Delivers a real notification to the given recipient(s) using the draft version's content — "
        "useful for previewing a workflow before committing it to live. "
        "For api-triggered workflows supply recipients and data; "
        "for event-triggered workflows supply distinct_id and event."
    )
    args_schema = DraftTriggerWorkflowInput
    permission_subcategory = "workflows"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        workflow_slug: str = "",
        version_id: str = "",
        trigger_type: str = "api",
        data: dict = None,
        recipients: list = None,
        actor: str = "",
        distinct_id: str = "",
        event: str = "",
        tenant_id: str = "",
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not workflow_slug:
            return "Error: workflow_slug is required.", {}
        if not version_id:
            return "Error: version_id is required.", {}

        body: dict = {
            "version_id": version_id,
            "trigger_type": trigger_type,
            "data": data or {},
        }
        if trigger_type == "api":
            if not recipients:
                return "Error: recipients is required for trigger_type='api'.", {}
            body["recipients"] = recipients
            if actor:
                body["actor"] = actor
        elif trigger_type == "event":
            if not distinct_id:
                return "Error: distinct_id is required for trigger_type='event'.", {}
            if not event:
                return "Error: event is required for trigger_type='event'.", {}
            body["distinct_id"] = distinct_id
            body["event"] = event
        if tenant_id:
            body["tenant_id"] = tenant_id

        try:
            result = await self._mgmnt_post(
                client,
                f"/v2/{ws}/workflow/{workflow_slug}/test_run/",
                body,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"test run for workflow '{workflow_slug}' version '{version_id}'")


# ── TestTemplateTool ──────────────────────────────────────────────────────────

class TestTemplateInput(BaseModel):
    template_slug: str = Field(description="Slug of the template to test.")
    distinct_id: str = Field(description="Recipient's distinct_id.")
    identities: list[dict] = Field(
        description=(
            "List of identity objects for the recipient. Each has identity_type and value (or value_json + id_provider). "
            "Examples: {\"identity_type\": \"email\", \"value\": \"user@example.com\"}, "
            "{\"identity_type\": \"androidpush\", \"value_json\": {\"token\": \"...\"}, \"id_provider\": \"fcm\"}"
        ),
    )
    category: str = Field(description="Notification category slug (e.g. 'system', 'transactional').")
    mode: Literal["draft", "live"] = Field(default="draft", description="'draft' to test the draft version, 'live' to test the published version.")
    tenant_id: str = Field(default="", description="Tenant ID (optional).")
    variant: dict | None = Field(default=None, description="Specific variant to test, e.g. {\"channel\": \"email\", \"id\": \"variant-a\"}.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class TestTemplateTool(ManagementTool):
    """POST {mgmnt_url}/v2/{ws}/template/{template_slug}/mock_test/?mode=draft|live"""

    name = "test_template"
    description = (
        "Send a test notification for a template to a specific recipient with supplied identities. "
        "Use mode='draft' to preview the draft version before committing, or mode='live' to test the published version. "
        "The recipient must have at least one identity (email, push token, phone number, etc.) provided via identities."
    )
    args_schema = TestTemplateInput
    permission_subcategory = "templates"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        distinct_id: str = "",
        identities: list = None,
        category: str = "",
        mode: str = "draft",
        tenant_id: str = "",
        variant: dict | None = None,
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not distinct_id:
            return "Error: distinct_id is required.", {}
        if not identities:
            return "Error: at least one identity is required.", {}
        if not category:
            return "Error: category is required.", {}

        body: dict = {
            "distinct_id": distinct_id,
            "identities": identities,
            "category": category,
        }
        if tenant_id:
            body["tenant_id"] = tenant_id
        if variant:
            body["variant"] = variant

        try:
            result = await self._mgmnt_post(
                client,
                f"/v2/{ws}/template/{template_slug}/mock_test/",
                body,
                params={"mode": mode},
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"test for template '{template_slug}' (mode={mode})")

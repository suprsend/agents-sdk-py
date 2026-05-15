import asyncio
import json

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool

_CHANNELS = Literal["email", "sms", "whatsapp", "androidpush", "iospush", "webpush", "inbox", "slack", "ms_teams", "webhook"]


def _parse_if_str(v):
    """Parse a JSON string into a Python object if needed."""
    if isinstance(v, str):
        return json.loads(v)
    return v


def _normalize_email_content(content: dict) -> dict:
    """
    Ensure email content.body is a dict.
    If body is a JSON-encoded string, parse it automatically.
    If body is a plain non-JSON string, raise a clear error.
    """
    body = content.get("body")
    if body is not None and isinstance(body, str):
        try:
            content["body"] = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            raise ValueError(
                "email content.body must be an object, not a plain string. "
                'Use: {"type": "raw", "raw": {"html": "<p>your content</p>"}}'
            )
    return content


# ── ListTemplatesTool ─────────────────────────────────────────────────────────

class ListTemplatesInput(BaseModel):
    search: str | None = Field(default=None, description="Text search on template name, slug, or description.")
    slugs: list[str] | None = Field(default=None, description="Filter to specific template slugs.")
    mode: Literal["draft", "live"] = Field(default="draft", description="'draft' returns in-progress version; 'live' returns only templates with a published version.")
    order_by: str | None = Field(default=None, description="Sort order: last_triggered_at, updated_at, -last_triggered_at, -updated_at.")
    limit: int | None = Field(default=None, description="Maximum number of results (max 50).")
    offset: int | None = Field(default=None, description="Number of results to skip for pagination.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("slugs", mode="before")
    @classmethod
    def parse_slugs(cls, v):
        return _parse_if_str(v)


class ListTemplatesTool(ManagementTool):
    """GET {mgmnt_url}/v2/{ws}/template/"""

    name = "list_templates"
    description = (
        "List templates in the workspace. Supports text search, slug filtering, and pagination. "
        "Use mode='draft' (default) to see all templates including unpublished ones, "
        "or mode='live' to see only templates with a published version."
    )
    args_schema = ListTemplatesInput
    permission_subcategory = "templates"
    permission_operation = "view"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        search: str | None = None,
        slugs: list | None = None,
        mode: str = "draft",
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.list,
                ws,
                search=search,
                slugs=slugs,
                mode=mode,
                order_by=order_by,
                limit=limit,
                offset=offset,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, "listing templates")


# ── GetTemplateTool ───────────────────────────────────────────────────────────

class GetTemplateInput(BaseModel):
    template_slug: str = Field(description="Slug of the template to fetch.")
    mode: Literal["draft", "live"] = Field(default="draft", description="'draft' returns the in-progress version; 'live' returns the last published version.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class GetTemplateTool(ManagementTool):
    """GET {mgmnt_url}/v2/{ws}/template/{slug}/"""

    name = "get_template"
    description = (
        "Fetch a single template by slug. Returns metadata, enabled channels, version info, "
        "and validation_result. Use mode='draft' (default) to inspect the current draft, "
        "or mode='live' to see the last published version. Returns 404 if slug not found "
        "or if mode='live' and no live version exists."
    )
    args_schema = GetTemplateInput
    permission_subcategory = "templates"
    permission_operation = "view"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        mode: str = "draft",
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.get,
                ws,
                template_slug,
                mode=mode,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"fetching template '{template_slug}'")


# ── GetTemplateVariantsTool ───────────────────────────────────────────────────

class GetTemplateVariantsInput(BaseModel):
    template_slug: str = Field(description="Slug of the template.")
    mode: Literal["draft", "live"] = Field(default="draft", description="Which version to read from.")
    channel: str | None = Field(default=None, description="Filter to a specific channel (email, sms, whatsapp, androidpush, iospush, webpush, inbox, slack, msteams, webhook).")
    include_content: bool = Field(default=False, description="Include full channel content in each variant. Omit for summary-only (faster).")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class GetTemplateVariantsTool(ManagementTool):
    """GET {mgmnt_url}/v2/{ws}/template/{slug}/variant/"""

    name = "get_template_variants"
    description = (
        "List all variants for a template across channels. Optionally filter by channel. "
        "Set include_content=true to fetch full content inline (expensive for many variants — "
        "prefer get_variant_content for a single variant). "
        "Ordered by channel rank → tenant_id (nulls first) → seq_no."
    )
    args_schema = GetTemplateVariantsInput
    permission_subcategory = "templates"
    permission_operation = "view"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        mode: str = "draft",
        channel: str | None = None,
        include_content: bool = False,
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.list_variants,
                ws,
                template_slug,
                mode=mode,
                channel=channel,
                include_content=include_content,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"fetching variants for template '{template_slug}'")


# ── GetVariantContentTool ─────────────────────────────────────────────────────

class GetVariantContentInput(BaseModel):
    template_slug: str = Field(description="Slug of the template.")
    channel: _CHANNELS = Field(description="Channel to fetch content for.")
    variant_id: str = Field(default="default", description="Variant identifier. Defaults to 'default'.")
    mode: Literal["draft", "live"] = Field(default="draft", description="Which version to read from.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class GetVariantContentTool(ManagementTool):
    """GET {mgmnt_url}/v2/{ws}/template/{slug}/channel/{channel}/variant/{variant_id}/content/"""

    name = "get_variant_content"
    description = (
        "Fetch the full content for a specific template variant (channel + variant_id). "
        "Returns the variant object with content and internal_content populated. "
        "For email, body will be the full email_body_def structure, not a plain string. "
        "Use this before modifying a variant to see what's currently saved."
    )
    args_schema = GetVariantContentInput
    permission_subcategory = "templates"
    permission_operation = "view"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        channel: str = "",
        variant_id: str = "default",
        mode: str = "draft",
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not channel:
            return "Error: channel is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.get_variant_content,
                ws,
                template_slug,
                channel,
                variant_id=variant_id,
                mode=mode,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"fetching variant content for '{template_slug}' channel '{channel}'")


# ── GetTemplateVersionsTool ───────────────────────────────────────────────────

class GetTemplateVersionsInput(BaseModel):
    template_slug: str = Field(description="Slug of the template.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class GetTemplateVersionsTool(ManagementTool):
    """GET {mgmnt_url}/v2/{ws}/template/{slug}/version/"""

    name = "get_template_versions"
    description = (
        "List published versions of a template ordered by version_no descending. "
        "Returns only published (active + inactive) versions — never draft. "
        "Each version includes: version_no, status, hash, commit_message, active_at, channels, variant summary."
    )
    args_schema = GetTemplateVersionsInput
    permission_subcategory = "templates"
    permission_operation = "view"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        **kwargs,
    ) -> tuple[str, list]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", []
        if not template_slug:
            return "Error: template_slug is required.", []
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.list_versions,
                ws,
                template_slug,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"fetching versions for template '{template_slug}'")


# ── GetMockDataTool ───────────────────────────────────────────────────────────

class GetMockDataInput(BaseModel):
    template_slug: str = Field(description="Slug of the template.")
    mode: Literal["draft", "live"] = Field(default="draft", description="Which version's mock data to fetch.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class GetMockDataTool(ManagementTool):
    """GET {mgmnt_url}/v2/{ws}/template/{slug}/mock_data/"""

    name = "get_mock_data"
    description = (
        "Fetch the mock data for a template. Mock data provides test values for template variables "
        "used during validate_template and validate_variant calls. "
        "The payload field under data holds handlebars variables — {{user.name}} maps to data.payload.user.name. "
        "Returns an initialized empty object if no mock data has been set yet (not an error)."
    )
    args_schema = GetMockDataInput
    permission_subcategory = "templates"
    permission_operation = "view"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        mode: str = "draft",
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.get_mock_data,
                ws,
                template_slug,
                mode=mode,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"fetching mock data for template '{template_slug}'")


# ── UpdateMockDataTool ────────────────────────────────────────────────────────

class UpdateMockDataInput(BaseModel):
    template_slug: str = Field(description="Slug of the template.")
    data: dict = Field(
        description=(
            "Mock data object. Key field is 'payload' — it holds the handlebars variables: "
            '{"payload": {"user": {"name": "Alice"}, "order": {"id": "ORD-123"}}, '
            '"recipient_distinct_id": "user-123"}. '
            "Other optional fields: tenant_id, is_batch, batch_count, recipient_sub_type, actor_*."
        )
    )
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("data", mode="before")
    @classmethod
    def parse_data(cls, v):
        return _parse_if_str(v)


class UpdateMockDataTool(ManagementTool):
    """PATCH {mgmnt_url}/v2/{ws}/template/{slug}/mock_data/"""

    name = "update_mock_data"
    description = (
        "Update the draft mock data for a template. Mock data is shared across all channels "
        "and used by validate_template and validate_variant for variable rendering. "
        "Only the draft version's mock data can be edited. "
        "The payload field under data is what feeds handlebars variable substitution."
    )
    args_schema = UpdateMockDataInput
    permission_subcategory = "templates"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        data: dict = None,
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not data:
            return "Error: data is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.update_mock_data,
                ws,
                template_slug,
                data,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"updating mock data for template '{template_slug}'")


# ── ValidateTemplateTool ──────────────────────────────────────────────────────

class ValidateTemplateVariantInput(BaseModel):
    channel: _CHANNELS
    variant_id: str = "default"
    locale: str = "en"
    content: dict
    needs_vendor_approval: bool = False

    @field_validator("content", mode="before")
    @classmethod
    def parse_content(cls, v):
        return _parse_if_str(v)


class ValidateTemplateInput(BaseModel):
    template_slug: str = Field(description="Slug of the template to validate.")
    name: str = Field(default="", description="Display name — required if the template does not exist yet.")
    description: str = Field(default="", description="Optional description.")
    tags: list[str] = Field(default_factory=list, description="Optional tags.")
    enabled_channels: list[str] = Field(default_factory=list, description="Channels this template supports.")
    variants: list[dict] = Field(
        description=(
            "List of variant objects to validate. Each entry must include: "
            "channel, content, and optionally variant_id (default='default'), locale (default='en'), "
            "needs_vendor_approval (default=false)."
        )
    )
    mock_data: dict = Field(
        default_factory=dict,
        description="Mock values for template variables used during rendering validation.",
    )
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("enabled_channels", "tags", "variants", mode="before")
    @classmethod
    def parse_list_fields(cls, v):
        return _parse_if_str(v)

    @model_validator(mode="after")
    def enforce_variant_content_shapes(self):
        for i, variant in enumerate(self.variants):
            if not isinstance(variant, dict):
                continue
            # parse nested string fields inside each variant
            for key in ("content", "mock_data"):
                if key in variant and isinstance(variant[key], str):
                    try:
                        variant[key] = json.loads(variant[key])
                    except (json.JSONDecodeError, ValueError):
                        pass
            if variant.get("channel") == "email":
                content = variant.get("content", {})
                if isinstance(content, dict):
                    try:
                        variant["content"] = _normalize_email_content(content)
                    except ValueError as e:
                        raise ValueError(f"variants[{i}]: {e}") from e
        return self

    @field_validator("mock_data", mode="before")
    @classmethod
    def parse_mock_data(cls, v):
        return _parse_if_str(v)


class ValidateTemplateTool(ManagementTool):
    """POST {mgmnt_url}/v2/{ws}/template/{slug}/validate/"""

    name = "validate_template"
    description = (
        "Full end-to-end template validation in a single call. Checks template group metadata "
        "and all variant content per channel. No DB writes — safe to call before the template exists. "
        "Response includes:\n"
        "  - action: 'create' | 'update' — whether upsert_template will create or update\n"
        "  - is_valid: overall validity\n"
        "  - template_group.is_valid + errors: metadata validation\n"
        "  - variants[].is_valid + errors + rendered content: per-channel validation\n"
        "Always call this FIRST before any upsert calls. Only proceed to upsert_template if is_valid is true.\n\n"
        "Email content shape — body must always be an object, never a plain string:\n"
        '  {"subject": "Hello {{user.name}}", "body": {"type": "raw", "raw": {"html": "<p>Hi</p>"}}}\n\n'
        "mock_data validation behavior per channel:\n"
        "  - email, sms (standard), androidpush, iospush, webpush, inbox, slack, msteams, webhook: mock_data is NOT validated — "
        "include it for rendering previews only, errors will never be raised against it.\n"
        "  - sms (DLT, needs_vendor_approval=true): mock_data IS validated — empty rendered variables "
        "raise errors on body.\n"
        "  - whatsapp: mock_data IS validated for body.text, header.text (TEXT format), "
        "header.media_url (if URL contains a variable), and CTA button url_dynamic_part — "
        "always provide complete mock_data when validating WhatsApp variants."
    )
    args_schema = ValidateTemplateInput
    permission_subcategory = "templates"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        name: str = "",
        description: str = "",
        tags: list = None,
        enabled_channels: list = None,
        variants: list = None,
        mock_data: dict = None,
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not variants:
            return "Error: at least one variant is required.", {}
        payload: dict = {"variants": variants}
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags
        if enabled_channels:
            payload["enabled_channels"] = enabled_channels
        if mock_data:
            payload["mock_data"] = mock_data
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.validate,
                ws,
                template_slug,
                payload,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"validating template '{template_slug}'")


# ── UpsertTemplateTool ────────────────────────────────────────────────────────

class UpsertTemplateInput(BaseModel):
    template_slug: str = Field(description="Slug identifier for the template.")
    name: str = Field(description="Display name for the template (required).")
    description: str = Field(default="", description="Optional description.")
    tags: list[str] = Field(default_factory=list, description="Optional list of tags.")
    enabled_channels: list[str] = Field(
        default_factory=list,
        description=(
            "Channels this template supports. Accepted values: "
            "email, sms, whatsapp, androidpush, iospush, webpush, inbox, slack, msteams, webhook."
        ),
    )
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("enabled_channels", "tags", mode="before")
    @classmethod
    def parse_list(cls, v):
        return _parse_if_str(v)


class UpsertTemplateTool(ManagementTool):
    """POST {mgmnt_url}/v2/{ws}/template/{slug}/"""

    name = "upsert_template"
    description = (
        "Create or update a template group — sets the name, description, enabled channels, "
        "and tags. Does NOT set channel content (use upsert_variant_content for that). "
        "Returns 201 for create, 202 for update."
    )
    args_schema = UpsertTemplateInput
    permission_subcategory = "templates"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        name: str = "",
        description: str = "",
        tags: list = None,
        enabled_channels: list = None,
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not name:
            return "Error: name is required.", {}
        payload = {"name": name}
        if description:
            payload["description"] = description
        if tags:
            payload["tags"] = tags
        if enabled_channels:
            payload["enabled_channels"] = enabled_channels
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.upsert,
                ws,
                template_slug,
                payload,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"upserting template '{template_slug}'")


# ── UpsertVariantContentTool ──────────────────────────────────────────────────

class UpsertVariantContentInput(BaseModel):
    template_slug: str = Field(description="Slug of the template to update.")
    channel: _CHANNELS = Field(description="Channel for this variant content.")
    content: dict = Field(description="Channel-specific content object.")
    variant_id: str = Field(default="default", description="Variant identifier. Defaults to 'default'.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("content", mode="before")
    @classmethod
    def parse_content(cls, v):
        return _parse_if_str(v)

    @model_validator(mode="after")
    def enforce_content_shape(self):
        if self.channel == "email":
            self.content = _normalize_email_content(self.content)
        return self


class UpsertVariantContentTool(ManagementTool):
    """PATCH {mgmnt_url}/v2/{ws}/template/{slug}/channel/{channel}/variant/{variant_id}/content/"""

    name = "upsert_variant_content"
    description = (
        "Set or update channel-specific content for a template variant. "
        "Call once per channel. variant_id defaults to 'default' for the primary variant.\n\n"
        "Content shape per channel — pass exactly as shown:\n\n"
        "  email:\n"
        '    {"subject": "Hello {{user.name}}", "body": {"type": "raw", "raw": {"html": "<p>Hi {{user.name}}</p>"}}}\n'
        "  IMPORTANT: email body must always be an object {type, raw} — never a plain string.\n\n"
        "  sms (standard):\n"
        '    {"text": "Your OTP is {{otp}}"}\n\n'
        "  sms (DLT/approval — needs_vendor_approval=true in validate_template):\n"
        '    {"type": "dlt", "body": "Your OTP is {{otp}}", "sender_id": "ABCDEF", "template_id": "1007xxxxxxxxxx"}\n\n'
        "  whatsapp:\n"
        '    {"category": "UTILITY", "body": {"text": "Hello {{user.name}}"}, '
        '"header": {"format": "TEXT", "text": "Order {{order.id}}"}, "footer": {"text": "Thank you"}, "button_type": "NONE"}\n\n'
        "  androidpush:\n"
        '    {"title": "New message", "body": "You have {{count}} unread messages",\n'
        '     "data": {}, "url": "deeplink://...", "image": "https://...",\n'
        '     "buttons": [{"id": "btn1", "label": "View", "url": "..."}]}\n'
        "  (data, url, image, buttons are optional)\n\n"
        "  iospush:\n"
        '    {"title": "New message", "body": "You have {{count}} unread messages",\n'
        '     "data": {}, "url": "deeplink://...", "badge": 1, "sound": "default"}\n'
        "  (data, url, badge, sound are optional)\n\n"
        "  webpush:\n"
        '    {"title": "New message", "body": "You have {{count}} unread messages", "url": "https://..."}\n'
    )
    args_schema = UpsertVariantContentInput
    permission_subcategory = "templates"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        channel: str = "",
        content: dict = None,
        variant_id: str = "default",
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not channel:
            return "Error: channel is required.", {}
        if not content:
            return "Error: content is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.upsert_variant_content,
                ws,
                template_slug,
                channel,
                variant_id,
                content,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"upserting variant content for '{template_slug}' channel '{channel}'")


# ── UpsertVariantTool ─────────────────────────────────────────────────────────

class UpsertVariantInput(BaseModel):
    template_slug: str = Field(description="Slug of the template.")
    channel: _CHANNELS = Field(description="Channel for this variant.")
    variant_id: str = Field(description="Variant identifier in the URL (e.g. 'default-fr', 'tenant-acme'). Must be unique within the channel.")
    locale: str = Field(description="BCP 47 locale code (e.g. 'en', 'fr', 'en-US'). Required for creation.")
    content: dict | None = Field(default=None, description="Channel-specific content object. Same shape as upsert_variant_content. Optional — can be set later via upsert_variant_content.")
    tenant_id: str | None = Field(default=None, description="Tenant identifier for tenant-scoped variants. Pass null for global variants.")
    conditions: list | None = Field(default=None, description="Targeting conditions for conditional variants. Pass [] for unconditional variants.")
    needs_vendor_approval: bool | None = Field(default=None, description="Set True for SMS DLT or WhatsApp templates requiring vendor approval.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("content", mode="before")
    @classmethod
    def parse_content(cls, v):
        return _parse_if_str(v) if v is not None else v

    @field_validator("conditions", mode="before")
    @classmethod
    def parse_conditions(cls, v):
        return _parse_if_str(v) if v is not None else v

    @model_validator(mode="after")
    def enforce_content_shape(self):
        if self.content is not None and self.channel == "email":
            self.content = _normalize_email_content(self.content)
        return self


class UpsertVariantTool(ManagementTool):
    """POST {mgmnt_url}/v2/{ws}/template/{slug}/channel/{channel}/variant/{variant_id}/"""

    name = "upsert_variant"
    description = (
        "Create or update a template variant. Use this when you need to add a NEW variant "
        "that does not exist yet (e.g. a French locale variant 'default-fr', or a tenant-scoped "
        "variant). Also use this to update an existing variant's locale, conditions, or "
        "needs_vendor_approval alongside its content in one call.\n\n"
        "Key distinction from upsert_variant_content:\n"
        "  - upsert_variant_content: PATCH — updates content of an EXISTING variant (404 if variant_id not found)\n"
        "  - upsert_variant (this tool): POST — creates variant if not found, updates if found. "
        "Always safe to call for new variant IDs.\n\n"
        "variant_id is the URL-level identifier (e.g. 'default', 'default-fr', 'tenant-acme-en'). "
        "locale determines the language (e.g. 'en', 'fr'). For the 'default' variant, "
        "locale and tenant_id cannot be changed after creation.\n\n"
        "Content shape per channel (same as upsert_variant_content):\n"
        "  email: {\"subject\": \"Hello {{user.name}}\", \"body\": {\"type\": \"raw\", \"raw\": {\"html\": \"<p>Hi</p>\"}}}\n"
        "  sms:   {\"text\": \"Your OTP is {{otp}}\"}\n"
        "  whatsapp: {\"category\": \"UTILITY\", \"body\": {\"text\": \"Hello {{name}}\"}}\n"
        "  androidpush/iospush: {\"title\": \"...\", \"body\": \"...\"}\n"
        "  webpush: {\"title\": \"...\", \"body\": \"...\", \"url\": \"https://...\"}\n"
    )
    args_schema = UpsertVariantInput
    permission_subcategory = "templates"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        channel: str = "",
        variant_id: str = "",
        locale: str = "",
        content: dict | None = None,
        tenant_id: str | None = None,
        conditions: list | None = None,
        needs_vendor_approval: bool | None = None,
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not channel:
            return "Error: channel is required.", {}
        if not variant_id:
            return "Error: variant_id is required.", {}
        if not locale:
            return "Error: locale is required.", {}
        payload: dict = {"locale": locale}
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id
        if conditions is not None:
            payload["conditions"] = conditions
        if needs_vendor_approval is not None:
            payload["needs_vendor_approval"] = needs_vendor_approval
        if content is not None:
            payload["content"] = content
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.upsert_variant,
                ws,
                template_slug,
                channel,
                variant_id,
                payload,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"upserting variant '{variant_id}' for '{template_slug}' channel '{channel}'")


# ── ValidateVariantTool ───────────────────────────────────────────────────────

class ValidateVariantInput(BaseModel):
    template_slug: str = Field(description="Slug of the template to validate.")
    channel: _CHANNELS = Field(description="Channel to validate content for.")
    content: dict = Field(description="Channel-specific content object to validate.")
    variant_id: str = Field(default="default", description="Variant identifier. Defaults to 'default'.")
    locale: str = Field(default="en", description="BCP 47 locale string (e.g. 'en', 'fr', 'en-US'). Max 30 chars.")
    mock_data: dict = Field(default_factory=dict, description="Mock data for template variable substitution. If omitted, uses template's stored mock data.")
    needs_vendor_approval: bool = Field(default=False, description="Set True for SMS/WhatsApp DLT-registered templates.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("content", "mock_data", mode="before")
    @classmethod
    def parse_dict(cls, v):
        return _parse_if_str(v)


class ValidateVariantTool(ManagementTool):
    """POST {mgmnt_url}/v2/{ws}/template/{slug}/validate_variant/"""

    name = "validate_variant"
    description = (
        "Stateless per-channel content validation — no DB writes. "
        "Call this BEFORE upsert_variant_content to confirm content is valid. "
        "Returns is_valid, errors, and rendered content so you can preview the output. "
        "If is_valid is false, fix errors and re-validate before saving."
    )
    args_schema = ValidateVariantInput
    permission_subcategory = "templates"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        channel: str = "",
        content: dict = None,
        variant_id: str = "default",
        locale: str = "en",
        mock_data: dict = None,
        needs_vendor_approval: bool = False,
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not channel:
            return "Error: channel is required.", {}
        if not content:
            return "Error: content is required.", {}
        payload = {
            "channel": channel,
            "variant_id": variant_id,
            "locale": locale,
            "content": content,
            "needs_vendor_approval": needs_vendor_approval,
        }
        if mock_data:
            payload["mock_data"] = mock_data
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.validate_variant,
                ws,
                template_slug,
                payload,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"validating variant for '{template_slug}' channel '{channel}'")


# ── PreCommitValidateTemplateTool ─────────────────────────────────────────────

class PreCommitValidateTemplateInput(BaseModel):
    template_slug: str = Field(description="Slug of the template to validate.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class PreCommitValidateTemplateTool(ManagementTool):
    """POST {mgmnt_url}/v2/{ws}/template/{slug}/pre_commit_validate/"""

    name = "pre_commit_validate_template"
    description = (
        "Run full draft validation across all channels and variants before committing. "
        "Returns is_valid, errors, and a diff vs the current live version. "
        "Call this after all upsert_variant_content calls are complete and before commit_template. "
        "If is_valid is false, fix the reported errors before committing."
    )
    args_schema = PreCommitValidateTemplateInput
    permission_subcategory = "templates"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.pre_commit_validate,
                ws,
                template_slug,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"pre-commit validating template '{template_slug}'")


# ── CommitTemplateTool ────────────────────────────────────────────────────────

class CommitTemplateInput(BaseModel):
    template_slug: str = Field(description="Slug of the template draft to publish.")
    variants: list[dict] = Field(
        description='List of variants to commit. Each entry: {"channel": "email", "id": "default"}.'
    )
    commit_message: str = Field(default="", description="Optional message describing what changed.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("variants", mode="before")
    @classmethod
    def parse_variants(cls, v):
        return _parse_if_str(v)


class CommitTemplateTool(ManagementTool):
    """PATCH {mgmnt_url}/v2/{ws}/template/{slug}/commit/"""

    name = "commit_template"
    description = (
        "Publish the current template draft as the new live version. "
        "Call this ONLY after pre_commit_validate_template has returned is_valid=true. "
        "Pass all variants that should go live. This is the final publish step — it will trigger HitL confirmation."
    )
    args_schema = CommitTemplateInput
    permission_subcategory = "templates"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        template_slug: str = "",
        variants: list = None,
        commit_message: str = "",
        **kwargs,
    ) -> tuple[str, dict]:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required.", {}
        if not template_slug:
            return "Error: template_slug is required.", {}
        if not variants:
            return "Error: variants list is required.", {}
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.templates.commit,
                ws,
                template_slug,
                variants,
                commit_message=commit_message,
                extra_headers=headers,
            )
            return json.dumps(result), result
        except Exception as e:
            return self._api_error(e, f"committing template '{template_slug}'")

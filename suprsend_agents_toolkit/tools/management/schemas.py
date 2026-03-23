import asyncio
import yaml

import json

from pydantic import BaseModel, Field, field_validator

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool


# ── ListSchemasTool ───────────────────────────────────────────────────────────

class ListSchemasInput(BaseModel):
    mode: str = Field(
        default="draft",
        description='Which version to list. "draft" shows latest draft; "live" shows committed versions.',
    )
    limit: int = Field(default=20, ge=1, le=100, description="Max schemas to return.")
    offset: int = Field(default=0, description="Pagination offset.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class ListSchemasTool(ManagementTool):
    """GET {mgmnt_url}/v1/{ws}/schema/"""

    name = "list_schemas"
    description = (
        "List trigger schemas defined in the workspace. Trigger schemas describe the JSON structure "
        "of API-triggered workflow payloads. Use mode='live' to see committed (deployed) schemas "
        "and mode='draft' to see schemas with pending changes."
    )
    args_schema = ListSchemasInput
    permission_subcategory = "schemas"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        mode: str = "draft",
        limit: int = 20,
        offset: int = 0,
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        mgmt, headers = self._mgmnt(client)
        try:
            result = await asyncio.to_thread(
                mgmt.schemas.list, ws, mode=mode, limit=limit, offset=offset, extra_headers=headers
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, "listing schemas")


# ── GetSchemaTool ─────────────────────────────────────────────────────────────

class GetSchemaInput(BaseModel):
    slug: str = Field(description="Schema slug to fetch.")
    mode: str = Field(
        default="draft",
        description='Which version to retrieve. "draft" shows the latest draft; "live" shows the committed version.',
    )
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class GetSchemaTool(ManagementTool):
    """GET {mgmnt_url}/v1/{ws}/schema/{slug}/"""

    name = "get_schema"
    description = (
        "Fetch a single trigger schema by slug. Returns the full JSON Schema definition, status "
        "(draft/live), version number, and linked workflows/events. "
        "Use mode='live' to read the currently deployed schema, 'draft' to see pending changes."
    )
    args_schema = GetSchemaInput
    permission_subcategory = "schemas"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        slug: str = "",
        mode: str = "draft",
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not slug:
            return "Error: slug is required."
        mgmt, headers = self._mgmnt(client)
        try:
            result = await asyncio.to_thread(
                mgmt.schemas.get, ws, slug, mode=mode, extra_headers=headers
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"fetching schema '{slug}'")


# ── PushSchemaTool ────────────────────────────────────────────────────────────

class PushSchemaInput(BaseModel):
    slug: str = Field(description="Schema slug. Created if it does not exist.")
    json_schema: dict = Field(
        description=(
            "JSON Schema object (draft 2020-12). Must include: "
            '"$schema": "https://json-schema.org/draft/2020-12/schema", '
            '"type": "object", and "properties" describing the trigger payload fields. '
            "Example: {\"$schema\": \"...\", \"type\": \"object\", \"title\": \"OrderCreated\", "
            "\"properties\": {\"order_id\": {\"type\": \"string\"}, \"amount\": {\"type\": \"number\"}}}"
        ),
    )
    name: str = Field(default="", description="Human-readable display name for the schema.")
    description: str = Field(default="", description="Description of what this schema validates.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")

    @field_validator("json_schema", mode="before")
    @classmethod
    def parse_json_schema(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class PushSchemaTool(ManagementTool):
    """POST {mgmnt_url}/v1/{ws}/schema/{slug}/"""

    name = "push_schema"
    description = (
        "Create or update a trigger schema definition. Saves as a draft — use commit_schema to deploy. "
        "The schema defines the JSON structure of API-triggered workflow payloads. "
        "After pushing and committing, link it to a workflow by including "
        "payload_schema in the workflow definition and committing the workflow."
    )
    args_schema = PushSchemaInput
    permission_subcategory = "schemas"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        slug: str = "",
        json_schema: dict = {},
        name: str = "",
        description: str = "",
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not slug:
            return "Error: slug is required."
        if not json_schema:
            return "Error: json_schema is required."
        mgmt, headers = self._mgmnt(client)
        try:
            result = await asyncio.to_thread(
                mgmt.schemas.push, ws, slug, json_schema, name=name, description=description, extra_headers=headers
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"pushing schema '{slug}'")


# ── CommitSchemaTool ──────────────────────────────────────────────────────────

class CommitSchemaInput(BaseModel):
    slug: str = Field(description="Schema slug to commit.")
    commit_message: str = Field(default="", description="Description of what changed in this version.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class CommitSchemaTool(ManagementTool):
    """PATCH {mgmnt_url}/v1/{ws}/schema/{slug}/commit/"""

    name = "commit_schema"
    description = (
        "Promote a trigger schema draft to live (deployed). Once committed, the schema is available "
        "to be linked to API-triggered workflows. To link to a workflow: include "
        "payload_schema: {schema: slug, version_no: null} in the workflow definition and commit the workflow."
    )
    args_schema = CommitSchemaInput
    permission_subcategory = "schemas"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        slug: str = "",
        commit_message: str = "",
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not slug:
            return "Error: slug is required."
        mgmt, headers = self._mgmnt(client)
        try:
            result = await asyncio.to_thread(
                mgmt.schemas.commit, ws, slug, commit_message=commit_message, extra_headers=headers
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"committing schema '{slug}'")


# ── LinkEventSchemaTool ───────────────────────────────────────────────────────

class LinkEventSchemaInput(BaseModel):
    event_ref: str = Field(description="Event name to link the schema to.")
    schema_slug: str = Field(description="Trigger schema slug to link.")
    workspace: str = Field(default="", description="Workspace slug. Uses configured default if omitted.")


class LinkEventSchemaTool(ManagementTool):
    """PATCH {mgmnt_url}/v1/{ws}/event/{event_ref}/"""

    name = "link_event_schema"
    description = (
        "Link a trigger schema to an event. Once linked, the schema validates the payload "
        "of any API call that publishes this event. The schema must be committed (live) before linking. "
        "The link is created immediately — no commit step required for events. "
        "Note: for API-triggered workflows, set payload_schema in the workflow definition and "
        "commit the workflow instead — the DefinitionLink is created automatically on workflow commit."
    )
    args_schema = LinkEventSchemaInput
    permission_subcategory = "schemas"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        event_ref: str = "",
        schema_slug: str = "",
        **kwargs,
    ):
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not event_ref:
            return "Error: event_ref is required."
        if not schema_slug:
            return "Error: schema_slug is required."
        mgmt, headers = self._mgmnt(client)
        try:
            result = await asyncio.to_thread(
                mgmt.events.link_schema, ws, event_ref, schema_slug, extra_headers=headers
            )
            return yaml.dump(result, default_flow_style=False), result
        except Exception as e:
            return self._api_error(e, f"linking schema '{schema_slug}' to event '{event_ref}'")

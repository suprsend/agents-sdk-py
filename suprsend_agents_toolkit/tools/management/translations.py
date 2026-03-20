import asyncio
import yaml

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.management import ManagementTool


class GetTranslationDetailsInput(BaseModel):
    filename: str = Field(
        description="The translation filename (e.g. 'en_common.json').",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class GetTranslationDetailsTool(ManagementTool):
    """GET {mgmnt_url}/v1/{ws}/translation/content/{filename}/"""

    name = "get_translation_details"
    description = (
        "Fetch the content of a translation file by its filename. "
        "Returns locale, namespace, and key-value translation content. "
        "Use this to inspect what translations are defined for a given locale and namespace."
    )
    args_schema = GetTranslationDetailsInput
    permission_subcategory = "translations"
    permission_operation = "read"
    read_only = True
    destructive = False
    idempotent = True
    open_world = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        filename: str = "",
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not filename:
            return "Error: filename is required."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.translations.get,
                ws,
                filename,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"fetching translation '{filename}' in workspace '{ws}'")


# ── UpdateTranslationTool ─────────────────────────────────────────────────────

class UpdateTranslationInput(BaseModel):
    filename: str = Field(
        description="The translation filename to create or update (e.g. 'en_common.json').",
    )
    content: dict = Field(
        description="Translation key-value pairs to store (e.g. {'greeting': 'Hello', 'farewell': 'Goodbye'}).",
    )
    workspace: str = Field(
        default="",
        description="Workspace slug. Uses configured default if omitted.",
    )


class UpdateTranslationTool(ManagementTool):
    """POST {mgmnt_url}/v1/{ws}/translation/content/{filename}/"""

    name = "update_translation"
    description = (
        "Create or update a translation file for a workspace. "
        "Provide the filename (e.g. 'en_common.json') and a dict of translation key-value pairs. "
        "Use this to add or overwrite localized strings used in notification templates."
    )
    args_schema = UpdateTranslationInput
    permission_subcategory = "translations"
    permission_operation = "manage"
    read_only = False
    destructive = False
    idempotent = True

    async def execute(
        self,
        client: AsyncSuprSendClient,
        filename: str = "",
        content: dict = {},
        **kwargs,
    ) -> str:
        ws = self._workspace(client, kwargs)
        if not ws:
            return "Error: workspace is required."
        if not filename:
            return "Error: filename is required."
        if not content:
            return "Error: content is required."
        try:
            mgmt, headers = self._mgmnt(client)
            result = await asyncio.to_thread(
                mgmt.translations.upsert,
                ws,
                filename,
                content,
                extra_headers=headers,
            )
            return yaml.dump(result, default_flow_style=False)
        except Exception as e:
            return self._api_error(e, f"updating translation '{filename}' in workspace '{ws}'")

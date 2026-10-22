import json

from pydantic import BaseModel, Field

from suprsend_agents_toolkit.client import AsyncSuprSendClient
from suprsend_agents_toolkit.core.base import SuprSendTool
from suprsend_agents_toolkit.tools._utils import evaluate_jsonnet_async


class ValidateJsonJsonnetInput(BaseModel):
    content: str = Field(
        description="The string to validate. Will be checked as JSON first, then as Jsonnet."
    )


class ValidateJsonJsonnetTool(SuprSendTool):
    name = "validate_json_jsonnet"
    description = (
        "Check whether a string is valid JSON or valid Jsonnet. "
        "Returns the detected format ('json' or 'jsonnet') on success, "
        "or a validation error message on failure. "
        "Use this before passing a payload string to any tool that accepts JSON or Jsonnet."
    )
    args_schema = ValidateJsonJsonnetInput
    read_only = True
    destructive = False
    idempotent = True
    open_world = False

    async def execute(
        self,
        client: AsyncSuprSendClient,
        content: str = "",
        **kwargs,
    ) -> str:
        if not content or not content.strip():
            return json.dumps({"valid": False, "error": "content is empty"})

        # Try JSON first
        try:
            json.loads(content)
            return json.dumps({"valid": True, "format": "json"})
        except json.JSONDecodeError:
            pass

        # Try Jsonnet
        try:
            await evaluate_jsonnet_async(content)
            return json.dumps({"valid": True, "format": "jsonnet"})
        except ImportError:
            return json.dumps({
                "valid": False,
                "error": "Not valid JSON. Jsonnet validation unavailable (install 'jsonnet' package).",
            })
        except Exception as e:
            return json.dumps({"valid": False, "error": str(e)})

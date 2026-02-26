from pydantic import BaseModel, Field

from suprsend_agents.client import AsyncSuprSendClient
from suprsend_agents.core.base import SuprSendTool

MINTLIFY_MCP_URL = "https://docs.suprsend.com/mcp"
MCP_TOOL_NAME = "SearchSuprSendNotification"


class SearchDocsInput(BaseModel):
    query: str = Field(description="Search query for SuprSend documentation.")


class SearchDocsTool(SuprSendTool):
    """
    Search SuprSend documentation via the Mintlify MCP server.

    No permission_category — always included in every toolkit.
    Does not use the HTTP client; connects directly to the MCP server.
    """

    name = "search_suprsend_docs"
    description = (
        "Search SuprSend documentation. Use this to find information about "
        "SuprSend features, APIs, SDKs, workflows, templates, and integrations."
    )
    args_schema = SearchDocsInput
    # no permission_category / permission_operation → always included

    async def execute(
        self,
        client: AsyncSuprSendClient,
        query: str = "",
        **_: object,
    ) -> str:
        if not query:
            return "Invalid query provided."

        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client

            async with streamablehttp_client(MINTLIFY_MCP_URL) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(MCP_TOOL_NAME, {"query": query})

                    if result.content:
                        text_parts = [c.text for c in result.content if hasattr(c, "text")]
                        return "\n".join(text_parts) if text_parts else "No results found."
                    return "No results found."

        except Exception as e:
            return f"Error searching docs: {e}"

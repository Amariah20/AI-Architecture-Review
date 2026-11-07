"""Retrieve AWS documentation through the AWS Knowledge MCP server."""

import asyncio
from dataclasses import dataclass
import json

from mcp import Client
from mcp.types import CallToolResult


SERVER_URL = "https://knowledge-mcp.global.api.aws"
TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class DocumentationResult:
    """A retrieved document excerpt and its source."""

    title: str
    url: str
    context: str


def parse_search_response(response: CallToolResult) -> list[DocumentationResult]:
    """Validate the observed AWS response format and extract documents."""
    if response.is_error:
        raise RuntimeError("AWS documentation search reported a tool error.")

    payload = response.structured_content
    if payload is None:
        text = "\n".join(
            block.text for block in response.content if block.type == "text"
        )
        if not text.strip():
            raise RuntimeError("Search returned no text or data.")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError("Search response is not valid JSON.") from error

    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected search response format.")
    content = payload.get("content")
    if not isinstance(content, dict):
        raise RuntimeError("Search response is missing its content object.")
    items = content.get("result")
    if not isinstance(items, list):
        raise RuntimeError("Search response is missing its result list.")
    if not items:
        raise RuntimeError("Search completed but returned no documentation results.")

    documents = []
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("Unexpected documentation result.")
        fields = [item.get(name) for name in ("title", "url", "context")]
        if not all(isinstance(value, str) and value.strip() for value in fields):
            raise RuntimeError("A result is missing its title, URL or excerpt.")
        documents.append(DocumentationResult(*fields))
    return documents


async def search_documentation(search_query: str) -> list[DocumentationResult]:
    """Search AWS guidance without terminal input or output."""
    search_query = search_query.strip()
    if not search_query:
        raise ValueError("Search query must not be empty.")

    async with asyncio.timeout(TIMEOUT_SECONDS):
        async with Client(SERVER_URL) as client:
            tools = []
            cursor = None
            while True:
                page = await client.list_tools(cursor=cursor)
                tools.extend(page.tools)
                if page.next_cursor is None:
                    break
                cursor = page.next_cursor

            matches = [
                tool for tool in tools
                if tool.name in ("search_documentation", "aws___search_documentation")
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"Expected one search_documentation tool, but found {len(matches)}."
                )

            response = await client.call_tool(
                matches[0].name,
                {"search_phrase": search_query, "topics": ["general"], "limit": 3},
            )

    return parse_search_response(response)

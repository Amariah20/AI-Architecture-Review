"""Test documentation retrieval using local, simulated MCP responses."""

import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from mcp.types import CallToolResult, TextContent, Tool


source_directory = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(source_directory))
try:
    documentation = importlib.import_module("architecture_review.aws_documentation")
    terminal = importlib.import_module("architecture_review.mcp_probe")
finally:
    sys.path.pop(0)


def payload() -> dict:
    return {"content": {"result": [{
        "title": "Synthetic document",
        "url": "https://docs.aws.amazon.com/example",
        "context": "Synthetic guidance for this test.",
    }]}}


class ResponseParsingTest(unittest.TestCase):
    def test_structured_and_json_text_responses(self) -> None:
        responses = [
            CallToolResult(content=[], structuredContent=payload()),
            CallToolResult(content=[TextContent(type="text", text=json.dumps(payload()))]),
        ]
        for response in responses:
            with self.subTest(response=response):
                results = documentation.parse_search_response(response)
                self.assertEqual(results, [documentation.DocumentationResult(
                    "Synthetic document", "https://docs.aws.amazon.com/example",
                    "Synthetic guidance for this test.",
                )])

    def test_invalid_empty_and_failed_responses(self) -> None:
        responses = [
            CallToolResult(content=[], isError=True),
            CallToolResult(content=[]),
            CallToolResult(content=[TextContent(type="text", text="not JSON")]),
        ]
        for invalid in ([], {}, {"content": []}, {"content": {}},
                        {"content": {"result": []}},
                        {"content": {"result": [None]}},
                        {"content": {"result": [{"title": " "}]}}):
            responses.append(CallToolResult(content=[], structuredContent=invalid))
        for response in responses:
            with self.subTest(response=response):
                with self.assertRaises(RuntimeError):
                    documentation.parse_search_response(response)


class RetrievalTest(unittest.IsolatedAsyncioTestCase):
    async def test_paginated_discovery_searches_once_without_printing(self) -> None:
        client = AsyncMock()
        client.list_tools.side_effect = [
            SimpleNamespace(tools=[], next_cursor="page-two"),
            SimpleNamespace(tools=[Tool(
                name="aws___search_documentation", inputSchema={},
            )], next_cursor=None),
        ]
        client.call_tool.return_value = CallToolResult(content=[], structuredContent=payload())
        with patch.object(documentation, "Client") as factory, patch("builtins.print") as output:
            factory.return_value.__aenter__.return_value = client
            results = await documentation.search_documentation("  RDS security  ")
            self.assertEqual(len(results), 1)
            self.assertEqual(client.list_tools.await_count, 2)
            client.call_tool.assert_awaited_once_with(
                "aws___search_documentation",
                {"search_phrase": "RDS security", "topics": ["general"], "limit": 3},
            )
            output.assert_not_called()
            factory.return_value.__aexit__.assert_awaited_once()

    async def test_blank_query_does_not_connect(self) -> None:
        with patch.object(documentation, "Client") as factory:
            with self.assertRaises(ValueError):
                await documentation.search_documentation("  ")
            factory.assert_not_called()

    async def test_custom_result_limit_is_sent_to_server(self) -> None:
        client = AsyncMock()
        client.list_tools.return_value = SimpleNamespace(tools=[Tool(
            name="aws___search_documentation", inputSchema={},
        )], next_cursor=None)
        client.call_tool.return_value = CallToolResult(content=[], structuredContent=payload())
        with patch.object(documentation, "Client") as factory:
            factory.return_value.__aenter__.return_value = client
            await documentation.search_documentation("RDS", limit=9)
            client.call_tool.assert_awaited_once_with(
                "aws___search_documentation",
                {"search_phrase": "RDS", "topics": ["general"], "limit": 9},
            )

    async def test_invalid_limit_does_not_connect(self) -> None:
        with patch.object(documentation, "Client") as factory:
            for limit in (0, 10, True, "9"):
                with self.subTest(limit=limit), self.assertRaises(ValueError):
                    await documentation.search_documentation("RDS", limit=limit)
            factory.assert_not_called()

    async def test_missing_tool_does_not_search(self) -> None:
        client = AsyncMock()
        client.list_tools.return_value = SimpleNamespace(tools=[], next_cursor=None)
        with patch.object(documentation, "Client") as factory:
            factory.return_value.__aenter__.return_value = client
            with self.assertRaisesRegex(RuntimeError, "found 0"):
                await documentation.search_documentation("RDS security")
            client.call_tool.assert_not_called()

    async def test_terminal_displays_returned_documents(self) -> None:
        result = documentation.DocumentationResult("Title", "https://docs.aws.amazon.com/example", "Excerpt")
        with (
            patch.object(terminal, "search_documentation", new_callable=AsyncMock, return_value=[result]) as search,
            patch("builtins.print") as output,
        ):
            await terminal.probe("RDS security")
            search.assert_awaited_once_with("RDS security")
            output.assert_any_call("Source: https://docs.aws.amazon.com/example")
            output.assert_any_call("Excerpt:\nExcerpt")

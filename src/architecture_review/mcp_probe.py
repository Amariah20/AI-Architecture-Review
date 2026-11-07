"""Connect to AWS Knowledge MCP and search official documentation."""

import asyncio
import json
import logging

from mcp import Client


SERVER_URL = "https://knowledge-mcp.global.api.aws"
TIMEOUT_SECONDS = 60
SEARCH_QUERY = "Amazon RDS public accessibility security best practices"


async def probe() -> None:
    """Discover documentation tools and run one fixed search."""
    async with asyncio.timeout(TIMEOUT_SECONDS):
        print(f"Connecting to {SERVER_URL}", flush=True)

        async with Client(SERVER_URL) as client:
            print("Connected.")
            print(f"Protocol version: {client.protocol_version}")

            tools = []
            cursor = None

            while True:
                page = await client.list_tools(cursor=cursor)
                tools.extend(page.tools)

                if page.next_cursor is None:
                    break

                cursor = page.next_cursor

            print("\nAvailable tools:")
            for tool in tools:
                print(f"- {tool.name}")

            documentation_tools = {}

            for expected_name in (
                "search_documentation",
                "read_documentation",
            ):
                matches = [
                    tool
                    for tool in tools
                    if tool.name == expected_name
                    or tool.name == f"aws___{expected_name}"
                ]

                if len(matches) != 1:
                    raise RuntimeError(
                        f"Expected one {expected_name} tool, "
                        f"but found {len(matches)}."
                    )

                documentation_tools[expected_name] = matches[0]

            # This runs once, after the discovery loop finishes.
            print(f"\nSearching: {SEARCH_QUERY}")

            result = await client.call_tool(
                documentation_tools["search_documentation"].name,
                {
                    "search_phrase": SEARCH_QUERY,
                    "topics": ["general"],
                    "limit": 3,
                },
            )

            if result.is_error:
                raise RuntimeError(
                    f"AWS documentation search failed: {result.content}"
                )

            # Prefer structured output. Otherwise, decode JSON text.
            payload = result.structured_content

            if payload is None:
                text = "\n".join(
                    block.text
                    for block in result.content
                    if block.type == "text"
                )

                if not text.strip():
                    raise RuntimeError("Search returned no text or data.")

                payload = json.loads(text)

            if not isinstance(payload, dict):
                raise RuntimeError("Unexpected search response format.")

            content = payload.get("content")

            if not isinstance(content, dict):
                raise RuntimeError(
                    "Search response is missing its content object."
                )

            results = content.get("result")

            if not isinstance(results, list):
                raise RuntimeError(
                    "Search response is missing its result list."
                )

            if not results:
                raise RuntimeError(
                    "Search completed but returned no documentation results."
                )

            for index, item in enumerate(results, start=1):
                if not isinstance(item, dict):
                    raise RuntimeError("Unexpected documentation result.")

                title = item.get("title")
                url = item.get("url")
                context = item.get("context")

                if not all(
                    isinstance(value, str) and value.strip()
                    for value in (title, url, context)
                ):
                    raise RuntimeError(
                        "A result is missing its title, URL or excerpt."
                    )

                print(f"\nResult {index}: {title}")
                print(f"Source: {url}")
                print(f"Excerpt:\n{context}")

        print("\nPASS: Retrieved documentation excerpts and source URLs.")


def main() -> int:
    """Run the probe and report failures."""
    logging.basicConfig(level=logging.WARNING)

    try:
        asyncio.run(probe())
    except TimeoutError:
        logging.error(
            "Connection probe exceeded %s seconds.",
            TIMEOUT_SECONDS,
        )
        return 1
    except Exception:
        logging.exception("Connection probe failed.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
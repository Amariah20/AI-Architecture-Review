"""Connect to AWS Knowledge MCP and search official documentation."""

import asyncio
import logging

from architecture_review.aws_documentation import TIMEOUT_SECONDS, search_documentation


async def probe(search_query: str) -> None:
    """Retrieve documentation and display it in the terminal."""
    print("Searching AWS documentation...", flush=True)
    results = await search_documentation(search_query)

    for index, item in enumerate(results, start=1):
        print(f"\nResult {index}: {item.title}")
        print(f"Source: {item.url}")
        print(f"Excerpt:\n{item.context}")

    print("\nPASS: Retrieved documentation excerpts and source URLs.")


def main() -> int:
    """Run the probe and report failures."""
    logging.basicConfig(level=logging.WARNING)

    try:
        print("Enter a synthetic AWS architecture description on one line.")
        print("This text will be sent to AWS documentation search.")
        print("Do not include credentials, private policies or company details.")
        search_query = input("Architecture: ").strip()

        if not search_query:
            logging.error("Architecture description must not be empty.")
            return 1

        asyncio.run(probe(search_query))
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return 1
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

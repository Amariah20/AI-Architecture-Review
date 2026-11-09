"""Exercise the web form using Streamlit's simulated application runner."""

import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

from streamlit.testing.v1 import AppTest


SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))
try:
    documentation = importlib.import_module("architecture_review.aws_documentation")
finally:
    sys.path.pop(0)


class WebAppTest(unittest.TestCase):
    def setUp(self) -> None:
        # Streamlit executes the file as a script; make the src package visible.
        sys.path.insert(0, str(SOURCE))
        self.addCleanup(sys.path.pop, 0)
        self.search = AsyncMock(return_value=[])
        patcher = patch.object(documentation, "search_documentation", self.search)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.app = AppTest.from_file(str(SOURCE / "architecture_review/web_app.py"), default_timeout=10)

    def submit(self, architecture: str = " EC2 and public RDS ", question: str = " Security risks? ") -> None:
        self.app.run()
        self.app.text_area[0].set_value(architecture)
        self.app.text_input[0].set_value(question)
        self.app.button[0].click().run()
        self.assertEqual(len(self.app.exception), 0)

    def test_initial_page_does_not_search(self) -> None:
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.text_area), 1)
        self.assertEqual(len(self.app.text_input), 1)
        self.assertEqual(len(self.app.selectbox), 0)
        self.search.assert_not_called()

    def test_both_fields_required_before_search(self) -> None:
        for architecture, question in ((" ", "Security?"), ("EC2", " ")):
            with self.subTest(architecture=architecture, question=question):
                self.submit(architecture, question)
                self.assertIn("Enter both", self.app.error[0].value)
                self.search.assert_not_called()

    def test_success_limits_results_and_preserves_sources(self) -> None:
        self.search.return_value = [documentation.DocumentationResult(
            f"Document {i}", f"https://docs.aws.amazon.com/example-{i}", f"Excerpt {i}",
        ) for i in range(4)]
        self.submit()
        self.search.assert_awaited_once_with("EC2 and public RDS\n\nReview question: Security risks?", limit=9)
        rendered = "\n".join(item.value for item in [*self.app.text, *self.app.markdown])
        for i in range(3):
            self.assertIn(f"Document {i}", rendered)
            self.assertIn(f"Excerpt {i}", rendered)
        self.assertNotIn("Document 3", rendered)
        self.assertEqual(len(self.app.get("link_button")), 3)
        for i, link in enumerate(self.app.get("link_button")):
            self.assertEqual(link.proto.url, f"https://docs.aws.amazon.com/example-{i}")
        self.assertFalse(any(item.value.startswith("Source:") for item in self.app.text))

    def test_timeout_message(self) -> None:
        self.search.side_effect = TimeoutError()
        self.submit()
        self.assertIn("timed out", self.app.error[0].value)

    def test_pagination_reuses_results_and_new_search_resets_page(self) -> None:
        self.search.return_value = [documentation.DocumentationResult(
            f"Document {i}", f"https://docs.aws.amazon.com/{i}", f"Excerpt {i}",
        ) for i in range(9)]
        self.app.run()
        self.app.text_area[0].set_value("EC2")
        self.app.text_input[0].set_value("Security?")
        self.app.button[0].click().run()
        self.assertTrue(self.app.button[1].disabled)
        self.app.button[5].click().run()
        self.assertIn("4. Document 3", [item.value for item in self.app.text])
        self.app.button[5].click().run()
        self.assertIn("7. Document 6", [item.value for item in self.app.text])
        self.assertTrue(self.app.button[5].disabled)
        self.app.button(key="page_1").click().run()
        self.assertIn("4. Document 3", [item.value for item in self.app.text])
        self.search.assert_awaited_once_with("EC2\n\nReview question: Security?", limit=9)
        self.app.button[0].click().run()
        self.assertIn("1. Document 0", [item.value for item in self.app.text])
        self.assertEqual(self.search.await_count, 2)

    def test_figure_note(self) -> None:
        self.search.return_value = [documentation.DocumentationResult(
            "Diagram", "https://docs.aws.amazon.com/example", "See Figure 2 for the network.",
        )]
        self.submit()
        self.assertTrue(any("Open the source page" in item.value for item in self.app.caption))

    def test_failure_is_useful_without_exposing_details(self) -> None:
        self.search.side_effect = RuntimeError("sensitive service detail")
        self.submit()
        self.assertIn("internet connection", self.app.error[0].value)
        self.assertNotIn("sensitive", self.app.error[0].value)

    def test_empty_results(self) -> None:
        self.submit()
        self.assertIn("No documentation found", self.app.warning[0].value)

    def test_excerpt_headings_and_links_are_formatted(self) -> None:
        self.search.return_value = [documentation.DocumentationResult(
            "Security", "https://docs.aws.amazon.com/example",
            "### Restrict access\n[Read guidance](https://docs.aws.amazon.com/example)\nhttps://aws.amazon.com/",
        )]
        self.submit()
        excerpts = [item.value for item in self.app.markdown]
        self.assertIn(
            "**Restrict access**\n[Read guidance](https://docs.aws.amazon.com/example)\nhttps://aws.amazon.com/",
            excerpts,
        )
        self.assertFalse(any('class="review-loading"' in value for value in excerpts))

    def test_formatter_preserves_code_and_removes_remote_images(self) -> None:
        web = importlib.import_module("architecture_review.web_app")
        self.assertEqual(
            web.format_excerpt("## Heading\n```python\n### comment\n```\n![image](https://example.com/image.png)"),
            "**Heading**\n```python\n### comment\n```\nimage",
        )

    def test_new_failed_search_does_not_show_old_results(self) -> None:
        self.search.return_value = [documentation.DocumentationResult("Old title", "https://docs.aws.amazon.com/old", "Old excerpt")]
        self.submit()
        self.search.side_effect = RuntimeError("unavailable")
        self.app.button[0].click().run()
        self.assertEqual(len(self.app.error), 1)
        self.assertEqual(len(self.app.text), 0)

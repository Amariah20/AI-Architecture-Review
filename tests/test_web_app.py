"""Exercise the workspace using simulated MCP results, never live AWS."""

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
    components = importlib.import_module("architecture_review.web_components")
finally:
    sys.path.pop(0)


class WebAppTest(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, str(SOURCE))
        self.addCleanup(sys.path.pop, 0)
        self.search = AsyncMock(return_value=[])
        patcher = patch.object(documentation, "search_documentation", self.search)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.app = AppTest.from_file(str(SOURCE / "architecture_review/web_app.py"), default_timeout=30)

    def submit(self, message: str = " EC2 and public RDS. Security risks? ") -> None:
        self.app.run()
        self.app.text_area(key="review_input").set_value(message)
        self.app.button(key="submit_review").click().run()
        self.assertEqual(len(self.app.exception), 0)

    def rendered(self) -> str:
        return "\n".join(item.value for item in [*self.app.text, *self.app.markdown, *self.app.caption])

    def sources(self, count: int = 4) -> list:
        return [documentation.DocumentationResult(f"Document {i}", f"https://docs.aws.amazon.com/example-{i}", f"Excerpt {i}") for i in range(count)]

    def test_initial_page_does_not_search(self) -> None:
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.text_area), 1)
        self.assertEqual(len(self.app.text_input), 0)
        self.assertEqual(len(self.app.selectbox), 0)
        self.search.assert_not_called()

    def test_icon_toolbar_and_no_synthetic_notice(self) -> None:
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertNotIn("Use synthetic examples only", self.rendered())
        self.assertNotIn("Theme switching is unavailable", self.rendered())
        self.assertEqual(len(self.app.get("iframe")), 0)

    def test_empty_input_does_not_search(self) -> None:
        for message in ("", "   "):
            with self.subTest(message=message):
                self.submit(message)
                self.assertIn("Enter your architecture", self.app.error[0].value)
                self.search.assert_not_called()

    def test_success_limits_results_and_preserves_sources(self) -> None:
        self.search.return_value = self.sources()
        self.submit()
        self.search.assert_awaited_once_with("EC2 and public RDS. Security risks?", limit=9)
        rendered = self.rendered()
        for i in range(3):
            self.assertIn(f"Document {i}", rendered)
            self.assertIn(f"Excerpt {i}", rendered)
        self.assertNotIn("Document 3", rendered)
        self.assertEqual(len(self.app.get("link_button")), 3)
        for i, link in enumerate(self.app.get("link_button")):
            self.assertEqual(link.proto.url, f"https://docs.aws.amazon.com/example-{i}")
        self.assertEqual(rendered.count(components.BEDROCK_PLACEHOLDER), 6)

    def test_multiple_questions_are_submitted_without_rewriting(self) -> None:
        message = "EC2 and RDS. Security risks? Multi-AZ costs? Recovery options?"
        self.submit(message)
        self.search.assert_awaited_once_with(message, limit=9)

    def test_timeout_message(self) -> None:
        self.search.side_effect = TimeoutError()
        self.submit()
        self.assertIn("timed out", self.app.error[0].value)

    def test_pagination_reuses_results_and_new_search_resets_page(self) -> None:
        self.search.return_value = self.sources(9)
        self.submit()
        self.assertTrue(self.app.button(key="previous_page").disabled)
        self.app.button(key="next_page").click().run()
        self.assertIn("Document 3", self.rendered())
        self.assertNotIn("Document 0", self.rendered())
        self.app.button(key="next_page").click().run()
        self.assertIn("Document 6", self.rendered())
        self.assertTrue(self.app.button(key="next_page").disabled)
        self.app.button(key="page_1").click().run()
        self.assertIn("Document 3", self.rendered())
        self.search.assert_awaited_once()
        self.app.button(key="submit_review").click().run()
        self.assertIn("Document 0", self.rendered())
        self.assertEqual(self.search.await_count, 2)

    def test_figure_note(self) -> None:
        self.search.return_value = [documentation.DocumentationResult("Diagram", "https://docs.aws.amazon.com/example", "See Figure 2 for the network.")]
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
        self.assertIn("**Restrict access**\n[Read guidance](https://docs.aws.amazon.com/example)\nhttps://aws.amazon.com/", excerpts)
        self.assertFalse(any('class="review-loading"' in value for value in excerpts))

    def test_formatter_preserves_code_and_removes_remote_images(self) -> None:
        self.assertEqual(components.format_excerpt("## Heading\n```python\n### comment\n```\n![image](https://example.com/image.png)"), "**Heading**\n```python\n### comment\n```\nimage")

    def test_new_failed_search_does_not_show_old_results(self) -> None:
        self.search.return_value = self.sources(1)
        self.submit()
        self.search.side_effect = RuntimeError("unavailable")
        self.app.button(key="submit_review").click().run()
        self.assertEqual(len(self.app.error), 1)
        self.assertNotIn("Document 0", self.rendered())

    def test_history_revisit_does_not_search_again(self) -> None:
        self.search.return_value = self.sources(1)
        self.submit("First architecture question")
        first = self.app.session_state["review_history"][0]
        self.app.text_area(key="review_input").set_value("Second architecture question")
        self.app.button(key="submit_review").click().run()
        self.app.button(key="nav_history").click().run()
        self.assertEqual(len(self.app.session_state["review_history"]), 2)
        self.app.button(key=f"history_{first.id}").click().run()
        self.assertEqual(self.app.text_area(key="review_input").value, "First architecture question")
        self.assertIn("Document 0", self.rendered())
        self.assertEqual(self.search.await_count, 2)

    def test_save_view_and_remove_source(self) -> None:
        source = self.sources(1)[0]
        self.search.return_value = [source]
        self.submit()
        key = components.source_key(source)
        self.app.button(key=f"save_result_{key}").click().run()
        self.assertEqual(len(self.app.session_state["saved_sources"]), 1)
        self.app.button(key="nav_saved").click().run()
        self.assertIn(source.title, self.rendered())
        self.assertTrue(any(link.proto.url == source.url for link in self.app.get("link_button")))
        self.app.button(key=f"save_saved_{key}").click().run()
        self.assertEqual(len(self.app.session_state["saved_sources"]), 0)

    def test_new_review_keeps_history_and_bookmarks(self) -> None:
        source = self.sources(1)[0]
        self.search.return_value = [source]
        self.submit()
        self.app.button(key=f"save_result_{components.source_key(source)}").click().run()
        self.app.button(key="nav_new").click().run()
        self.assertEqual(self.app.text_area(key="review_input").value, "")
        self.assertEqual(len(self.app.session_state["review_history"]), 1)
        self.assertEqual(len(self.app.session_state["saved_sources"]), 1)
        self.assertIsNone(self.app.session_state["active_review_id"])

    def test_long_excerpts_have_expansion(self) -> None:
        self.search.return_value = [documentation.DocumentationResult("Long source", "https://docs.aws.amazon.com/example", "Actual source text. " * 100)]
        self.submit()
        key = components.source_key(self.search.return_value[0])
        self.assertFalse(any(item.label == "Read full retrieved excerpt" for item in self.app.expander))
        self.app.button(key=f"excerpt_button_result_{key}").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertIn(("Actual source text. " * 100).strip(), self.rendered())
        self.assertEqual(self.search.await_count, 1)

    def test_results_omit_context_and_host_caption(self) -> None:
        self.search.return_value = self.sources(1)
        self.submit()
        self.assertNotIn("Review context", [item.label for item in self.app.expander])
        self.assertFalse(any("AWS documentation ·" in item.value for item in self.app.caption))

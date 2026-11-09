"""Session history and bookmark state without Streamlit or network access."""

import importlib
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))
try:
    session = importlib.import_module("architecture_review.review_session")
    DocumentationResult = importlib.import_module("architecture_review.aws_documentation").DocumentationResult
finally:
    sys.path.pop(0)


class ReviewSessionTest(unittest.TestCase):
    def test_history_keeps_immutable_source_snapshot(self) -> None:
        state = {}
        session.initialise(state)
        source = DocumentationResult("Original", "https://docs.aws.amazon.com/one", "Excerpt")
        sources = [source]
        entry = session.record_review(state, "Architecture question", sources, ("policy.txt",))
        sources.clear()
        self.assertEqual(entry.sources, (source,))
        self.assertEqual(entry.policy_names, ("policy.txt",))
        session.open_review(state, entry.id)
        self.assertEqual(state["review_input"], "Architecture question")
        self.assertEqual(len(state["review_history"]), 1)

    def test_bookmarks_unique_by_url_across_searches(self) -> None:
        state = {}
        session.initialise(state)
        source = DocumentationResult("Original", "https://docs.aws.amazon.com/one", "Excerpt")
        session.toggle_saved_source(state, source)
        session.record_review(state, "First", [source], ())
        session.record_review(state, "Second", [source], ())
        self.assertEqual(len(state["saved_sources"]), 1)
        session.toggle_saved_source(state, source)
        self.assertFalse(state["saved_sources"])

    def test_new_review_removes_policy_content_but_keeps_session_history(self) -> None:
        state = {}
        session.initialise(state)
        entry = session.record_review(state, "Question", [], ())
        state["policy_documents"] = {"one": object()}
        state["review_error"] = "Old error"
        session.new_review(state)
        self.assertFalse(state["policy_documents"])
        self.assertEqual(state["review_history"], [entry])
        self.assertNotIn("review_error", state)

    def test_duplicate_source_urls_do_not_create_duplicate_cards(self) -> None:
        state = {}
        session.initialise(state)
        source = DocumentationResult("Original", "https://docs.aws.amazon.com/one", "Excerpt")
        entry = session.record_review(state, "Question", [source, source], ())
        self.assertEqual(entry.sources, (source,))

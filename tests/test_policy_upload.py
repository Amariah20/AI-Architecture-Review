"""UI checks using synthetic in-memory uploads; no browser or AWS required."""

import importlib
from dataclasses import replace
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from streamlit.testing.v1 import AppTest

from test_document_processing import pdf_bytes


SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))
try:
    policy_ui = importlib.import_module("architecture_review.policy_upload")
    documentation = importlib.import_module("architecture_review.aws_documentation")
finally:
    sys.path.pop(0)


class PolicyUploadTest(unittest.TestCase):
    def setUp(self) -> None:
        sys.path.insert(0, str(SOURCE))
        self.addCleanup(sys.path.pop, 0)
        self.environment = patch.dict(os.environ, {"APP_ENV": "production", "POLICY_DEV_PREVIEW": "false", "POLICY_DEV_FIRST_LINES": "false", "POLICY_MAX_UPLOAD_MB": "10"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        ocr_patcher = patch.object(policy_ui, "recognize_flagged_pages", side_effect=lambda document, data: document)
        self.ocr_mock = ocr_patcher.start()
        self.addCleanup(ocr_patcher.stop)
        self.app = AppTest.from_file(str(SOURCE / "architecture_review/web_app.py"), default_timeout=30)

    def upload(self, name: str, data: bytes) -> SimpleNamespace:
        return SimpleNamespace(name=name, size=len(data), getvalue=lambda: data)

    def visible_text(self) -> str:
        return "\n".join(element.value for collection in (
            self.app.text, self.app.markdown, self.app.caption, self.app.warning, self.app.error,
        ) for element in collection)

    def test_upload_is_retained_without_display_or_mcp_call(self) -> None:
        upload = self.upload("synthetic.txt", b"CONFIDENTIAL_SENTINEL synthetic content")
        with (
            patch("streamlit.file_uploader", return_value=upload),
            patch.object(documentation, "search_documentation", new_callable=AsyncMock) as search,
            patch.object(policy_ui, "process_document", wraps=policy_ui.process_document) as process,
        ):
            self.app.run()
            self.assertFalse(self.app.exception)
            self.assertIn("synthetic.txt", self.visible_text())
            self.assertNotIn("CONFIDENTIAL_SENTINEL", self.visible_text())
            self.assertEqual(self.app.session_state["policy_document"].status, "readable")
            self.app.run()
            process.assert_called_once()
            search.assert_not_called()

    def test_scanned_page_locations_are_displayed(self) -> None:
        with patch("streamlit.file_uploader", return_value=self.upload("mixed.pdf", pdf_bytes(["Text", None]))):
            self.app.run()
            self.assertFalse(self.app.exception)
            self.assertIn("Partially readable", self.visible_text())
            self.assertIn("Page 2", self.visible_text())
            self.assertIn("may contain scanned", self.visible_text())
            self.app.run()
            self.ocr_mock.assert_called_once()

    def test_native_pdf_does_not_need_ocr(self) -> None:
        with patch("streamlit.file_uploader", return_value=self.upload("native.pdf", pdf_bytes(["Readable text"]))):
            self.app.run()
            self.ocr_mock.assert_not_called()

    def test_legacy_debug_flags_cannot_display_extracted_text(self) -> None:
        with (
            patch.dict(os.environ, {"APP_ENV": "development", "POLICY_DEV_PREVIEW": "true", "POLICY_DEV_FIRST_LINES": "true"}),
            patch("streamlit.file_uploader", return_value=self.upload("policy.pdf", pdf_bytes(["CONFIDENTIAL_SENTINEL"]))),
        ):
            self.app.run()
            self.assertFalse(self.app.exception)
            self.assertNotIn("CONFIDENTIAL_SENTINEL", self.visible_text())
            self.assertFalse(any("preview" in item.label.lower() or "development check" in item.label.lower()
                                 for item in self.app.expander))



    def test_remove_upload_clears_policy(self) -> None:
        with patch("streamlit.file_uploader", return_value=self.upload("policy.txt", b"Synthetic policy")):
            self.app.run()
            self.assertIn("policy_document", self.app.session_state)
        with patch("streamlit.file_uploader", return_value=None):
            self.app.run()
            self.assertNotIn("policy_document", self.app.session_state)

    def test_oversized_upload_is_rejected_before_reading(self) -> None:
        upload = self.upload("huge.txt", b"synthetic")
        upload.size = 11 * 1024 * 1024
        with (
            patch("streamlit.file_uploader", return_value=upload),
            patch.object(policy_ui, "process_document") as process,
        ):
            self.app.run()
            self.assertIn("size limit", self.visible_text())
            process.assert_not_called()
            self.assertNotIn("policy_document", self.app.session_state)

    def test_corruption_has_safe_error(self) -> None:
        with patch("streamlit.file_uploader", return_value=self.upload("broken.pdf", b"%PDF-CONFIDENTIAL_SENTINEL")):
            self.app.run()
            self.assertTrue(self.app.error)
            self.assertNotIn("CONFIDENTIAL_SENTINEL", self.visible_text())

    def test_upload_text_is_not_added_to_explicit_aws_search(self) -> None:
        with (
            patch("streamlit.file_uploader", return_value=self.upload("policy.txt", b"CONFIDENTIAL_SENTINEL")),
            patch.object(documentation, "search_documentation", new_callable=AsyncMock, return_value=[]) as search,
        ):
            self.app.run()
            self.app.text_area[0].set_value("Synthetic EC2 application")
            self.app.text_input[0].set_value("Reliability guidance?")
            self.app.button[0].click().run()
            search.assert_awaited_once_with(
                "Synthetic EC2 application\n\nReview question: Reliability guidance?", limit=9,
            )

    def test_replacing_upload_releases_previous_policy_even_on_failure(self) -> None:
        with patch("streamlit.file_uploader", return_value=self.upload("policy.txt", b"Old synthetic policy")):
            self.app.run()
        new_upload = self.upload("broken.pdf", b"%PDF-broken")

        def changed_upload(*args: object, **kwargs: object) -> SimpleNamespace:
            # Simulate Streamlit's uploader callback on a replacement file.
            kwargs["on_change"]()
            return new_upload

        with patch("streamlit.file_uploader", side_effect=changed_upload):
            self.app.run()
            self.assertNotIn("policy_document", self.app.session_state)
            self.assertNotIn("Old synthetic policy", self.visible_text())
            self.assertTrue(self.app.error)

    def test_automatic_ocr_keeps_text_in_memory_without_displaying_it(self) -> None:
        data = pdf_bytes(["Native first line", None])
        native = policy_ui.process_document("mixed.pdf", data)
        recognised = replace(native.passages[1], text="OCR first line\nOCR second line\nThird line stays hidden",
                             status="readable", may_require_ocr=False, ocr_attempted=True,
                             extraction_method="ocr", warnings=("Verify OCR text.",))
        result = replace(native, passages=(native.passages[0], recognised), status="needs_processing")
        with (
            patch.dict(os.environ, {"APP_ENV": "development", "POLICY_DEV_FIRST_LINES": "true"}),
            patch("streamlit.file_uploader", return_value=self.upload("mixed.pdf", data)),
            patch.object(policy_ui, "recognize_flagged_pages", return_value=result) as recognize,
        ):
            self.app.run()
            self.assertNotIn("Native first line", self.visible_text())
            self.assertFalse(self.app.exception)
            self.assertNotIn("OCR first line", self.visible_text())
            self.assertIn("OCR first line", self.app.session_state["policy_document"].passages[1].text)
            self.assertFalse(any("development" in item.label.lower() for item in self.app.expander))
            self.assertNotIn("Third line stays hidden", self.visible_text())
            self.assertFalse(any(button.label == "Try text recognition" for button in self.app.button))
            self.app.run()
            recognize.assert_called_once()


    def test_ocr_error_does_not_erase_native_extraction(self) -> None:
        data = pdf_bytes(["Native policy", None])
        with (
            patch("streamlit.file_uploader", return_value=self.upload("mixed.pdf", data)),
            patch.object(policy_ui, "recognize_flagged_pages", side_effect=policy_ui.OcrError("Engine unavailable")),
        ):
            self.app.run()
            self.assertIn("Engine unavailable", self.visible_text())
            self.assertIn("Native policy", self.app.session_state["policy_document"].passages[0].text)

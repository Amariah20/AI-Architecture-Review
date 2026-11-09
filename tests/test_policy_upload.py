"""Synthetic multi-upload UI tests; extracted policy text must stay hidden."""

import importlib
from dataclasses import replace
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

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
        patcher = patch.dict(os.environ, {"POLICY_MAX_UPLOAD_MB": "10"})
        patcher.start()
        self.addCleanup(patcher.stop)
        ocr_patcher = patch.object(policy_ui, "recognize_flagged_pages", side_effect=lambda document, data: document)
        self.ocr_mock = ocr_patcher.start()
        self.addCleanup(ocr_patcher.stop)
        self.app = AppTest.from_file(str(SOURCE / "architecture_review/web_app.py"), default_timeout=30)

    def upload(self, name: str, data: bytes) -> SimpleNamespace:
        return SimpleNamespace(name=name, size=len(data), file_id=uuid4().hex, getvalue=lambda: data)

    def visible_text(self) -> str:
        return "\n".join(element.value for collection in (self.app.text, self.app.markdown, self.app.caption, self.app.warning, self.app.error) for element in collection)

    def records(self) -> list:
        return list(self.app.session_state["policy_documents"].values())

    def test_upload_is_retained_without_display_or_mcp_call(self) -> None:
        upload = self.upload("synthetic.txt", b"CONFIDENTIAL_SENTINEL synthetic content")
        with (patch("streamlit.file_uploader", return_value=[upload]),
              patch.object(documentation, "search_documentation", new_callable=AsyncMock) as search,
              patch.object(policy_ui, "process_document", wraps=policy_ui.process_document) as process):
            self.app.run()
            self.assertFalse(self.app.exception)
            self.assertIn("synthetic.txt", self.visible_text())
            self.assertNotIn("CONFIDENTIAL_SENTINEL", self.visible_text())
            self.assertEqual(self.records()[0].document.status, "readable")
            self.app.run()
            process.assert_called_once()
            search.assert_not_called()

    def test_scanned_page_locations_are_displayed(self) -> None:
        with patch("streamlit.file_uploader", return_value=[self.upload("mixed.pdf", pdf_bytes(["Text", None]))]):
            self.app.run()
            self.assertFalse(self.app.exception)
            self.assertIn("Manual review needed", self.visible_text())
            self.assertIn('class="policy-status-warning"', self.visible_text())
            self.assertIn("Page 2", self.visible_text())
            self.app.run()
            self.ocr_mock.assert_called_once()

    def test_native_pdf_does_not_need_ocr(self) -> None:
        with patch("streamlit.file_uploader", return_value=[self.upload("native.pdf", pdf_bytes(["Readable text"]))]):
            self.app.run()
            self.ocr_mock.assert_not_called()

    def test_legacy_debug_flags_cannot_display_extracted_text(self) -> None:
        with (patch.dict(os.environ, {"APP_ENV": "development", "POLICY_DEV_PREVIEW": "true", "POLICY_DEV_FIRST_LINES": "true"}),
              patch("streamlit.file_uploader", return_value=[self.upload("policy.pdf", pdf_bytes(["CONFIDENTIAL_SENTINEL"]))])):
            self.app.run()
            self.assertNotIn("CONFIDENTIAL_SENTINEL", self.visible_text())

    def test_remove_upload_clears_its_extracted_content(self) -> None:
        with patch("streamlit.file_uploader", return_value=[self.upload("policy.txt", b"Synthetic policy")]):
            self.app.run()
            identifier = self.records()[0].id
            self.assertEqual(self.app.button(key=f"remove_policy_{identifier}").label, "")
            self.app.button(key=f"remove_policy_{identifier}").click().run()
            self.assertEqual(self.records(), [])

    def test_oversized_upload_is_rejected_before_reading(self) -> None:
        upload = self.upload("huge.txt", b"synthetic")
        upload.size = 11 * 1024 * 1024
        with (patch("streamlit.file_uploader", return_value=[upload]), patch.object(policy_ui, "process_document") as process):
            self.app.run()
            self.assertIn("size limit", self.visible_text())
            process.assert_not_called()
            self.assertIsNone(self.records()[0].document)

    def test_corruption_has_safe_error(self) -> None:
        with patch("streamlit.file_uploader", return_value=[self.upload("broken.pdf", b"%PDF-CONFIDENTIAL_SENTINEL")]):
            self.app.run()
            self.assertTrue(self.app.error)
            self.assertIn('class="policy-status-error"', self.visible_text())
            self.assertNotIn("CONFIDENTIAL_SENTINEL", self.visible_text())

    def test_upload_text_is_not_added_to_explicit_aws_search(self) -> None:
        with (patch("streamlit.file_uploader", return_value=[self.upload("policy.txt", b"CONFIDENTIAL_SENTINEL")]),
              patch.object(documentation, "search_documentation", new_callable=AsyncMock, return_value=[]) as search):
            self.app.run()
            self.app.text_area(key="review_input").set_value("Synthetic EC2 application. Reliability guidance?")
            self.app.button(key="submit_review").click().run()
            search.assert_awaited_once_with("Synthetic EC2 application. Reliability guidance?", limit=9)

    def test_bad_later_upload_does_not_erase_previous_policy(self) -> None:
        with patch("streamlit.file_uploader", return_value=[self.upload("policy.txt", b"Old synthetic policy")]):
            self.app.run()
        with patch("streamlit.file_uploader", return_value=[self.upload("broken.pdf", b"%PDF-broken")]):
            self.app.run()
            self.assertEqual(len(self.records()), 2)
            self.assertEqual(self.records()[0].document.passages[0].text, "Old synthetic policy")
            self.assertIsNone(self.records()[1].document)
            self.assertNotIn("Old synthetic policy", self.visible_text())

    def test_automatic_ocr_keeps_text_in_memory_without_displaying_it(self) -> None:
        data = pdf_bytes(["Native first line", None])
        native = policy_ui.process_document("mixed.pdf", data)
        recognised = replace(native.passages[1], text="OCR first line\nOCR second line", status="readable", may_require_ocr=False, ocr_attempted=True, extraction_method="ocr", warnings=("Verify OCR text.",))
        result = replace(native, passages=(native.passages[0], recognised), status="needs_processing")
        with (patch("streamlit.file_uploader", return_value=[self.upload("mixed.pdf", data)]),
              patch.object(policy_ui, "recognize_flagged_pages", return_value=result) as recognize):
            self.app.run()
            self.assertNotIn("Native first line", self.visible_text())
            self.assertNotIn("OCR first line", self.visible_text())
            self.assertIn("OCR first line", self.records()[0].document.passages[1].text)
            self.assertIn("Text extracted (OCR)", self.visible_text())
            self.app.run()
            recognize.assert_called_once()

    def test_ocr_error_does_not_erase_native_extraction(self) -> None:
        data = pdf_bytes(["Native policy", None])
        with (patch("streamlit.file_uploader", return_value=[self.upload("mixed.pdf", data)]),
              patch.object(policy_ui, "recognize_flagged_pages", side_effect=policy_ui.OcrError("Engine unavailable"))):
            self.app.run()
            self.assertIn("Engine unavailable", self.visible_text())
            self.assertIn("Native policy", self.records()[0].document.passages[0].text)

    def test_sequential_uploads_and_individual_removal(self) -> None:
        for name in ("a.txt", "b.txt", "c.txt"):
            with patch("streamlit.file_uploader", return_value=[self.upload(name, b"Synthetic policy")]):
                self.app.run()
        self.assertEqual([r.filename for r in self.records()], ["a.txt", "b.txt", "c.txt"])
        identifier = self.records()[1].id
        self.app.button(key=f"remove_policy_{identifier}").click().run()
        self.assertEqual([r.filename for r in self.records()], ["a.txt", "c.txt"])

    def test_duplicate_names_do_not_overwrite_and_identical_files_are_deduplicated(self) -> None:
        for content in (b"Policy A", b"Policy B", b"Policy A"):
            with patch("streamlit.file_uploader", return_value=[self.upload("same.txt", content)]):
                self.app.run()
        self.assertEqual(len(self.records()), 2)
        self.assertEqual([r.document.passages[0].text for r in self.records()], ["Policy A", "Policy B"])
        self.assertIn("document 2 with this name", self.visible_text())

    def test_clear_all_releases_document_records(self) -> None:
        with patch("streamlit.file_uploader", return_value=[self.upload("a.txt", b"Policy")]):
            self.app.run()
        self.app.button(key="clear_policies").click().run()
        self.assertFalse(self.records())

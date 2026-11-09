"""Local OCR tests, including real synthetic image text when Tesseract exists."""

from dataclasses import replace
from io import BytesIO
import importlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter

from test_document_processing import pdf_bytes


SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))
try:
    ocr = importlib.import_module("architecture_review.ocr")
    processing = importlib.import_module("architecture_review.document_processing")
    settings_module = importlib.import_module("architecture_review.document_settings")
finally:
    sys.path.pop(0)


def scanned_pdf() -> bytes:
    image = Image.new("RGB", (1200, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 60), "SYNTHETIC POLICY PAGE", font=ImageFont.load_default(size=44), fill="black")
    draw.text((40, 150), "Keep databases private.", font=ImageFont.load_default(size=36), fill="black")
    output = BytesIO()
    image.save(output, format="PDF", resolution=150)
    image.close()
    return output.getvalue()


class OcrTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = pdf_bytes(["Native page", None, None])
        self.document = processing.process_document("mixed.pdf", self.data)

    def test_only_flagged_pages_are_replaced_and_native_text_is_preserved(self) -> None:
        with (
            patch.object(ocr, "find_tesseract", return_value="engine"),
            patch.object(ocr, "verify_tesseract"),
            patch.object(ocr, "_render_page", return_value=b"PNG") as render,
            patch.object(ocr, "_recognize_image", return_value="Recognised policy"),
        ):
            result = ocr.recognize_flagged_pages(self.document, self.data)
        self.assertEqual(result.passages[0], self.document.passages[0])
        self.assertEqual([call.args[1] for call in render.call_args_list], [2, 3])
        self.assertEqual(result.passages[1].page_number, 2)
        self.assertEqual(result.passages[1].extraction_method, "ocr")
        self.assertFalse(result.passages[1].may_require_ocr)
        self.assertEqual(result.status, "needs_processing")
        self.assertTrue(result.requires_further_processing)

    def test_blank_and_timed_out_pages_remain_flagged(self) -> None:
        with (
            patch.object(ocr, "find_tesseract", return_value="engine"),
            patch.object(ocr, "verify_tesseract"),
            patch.object(ocr, "_render_page", return_value=b"PNG"),
            patch.object(ocr, "_recognize_image", side_effect=["", subprocess.TimeoutExpired("engine", 1)]),
        ):
            result = ocr.recognize_flagged_pages(self.document, self.data)
        self.assertTrue(all(part.may_require_ocr and part.ocr_attempted for part in result.passages[1:]))
        self.assertIn("timed out", result.passages[2].warnings[0])

    def test_page_cap_and_continuation_skip_attempted_pages(self) -> None:
        with (
            patch.object(ocr, "find_tesseract", return_value="engine"),
            patch.object(ocr, "verify_tesseract"),
            patch.object(ocr, "_render_page", return_value=b"PNG") as render,
            patch.object(ocr, "_recognize_image", return_value="Policy"),
        ):
            result = ocr.recognize_flagged_pages(self.document, self.data, ocr.OcrLimits(max_pages=1))
            self.assertFalse(result.passages[2].ocr_attempted)
            result = ocr.recognize_flagged_pages(result, self.data, ocr.OcrLimits(max_pages=1))
            self.assertEqual([call.args[1] for call in render.call_args_list], [2, 3])
            self.assertTrue(result.passages[2].ocr_attempted)

    def test_changed_upload_is_rejected_before_starting_processes(self) -> None:
        with patch.object(ocr, "_run") as run, self.assertRaises(ocr.OcrError):
            ocr.recognize_flagged_pages(self.document, pdf_bytes(["Different PDF"]))
        run.assert_not_called()

    def test_missing_engine_preserves_original_document(self) -> None:
        with patch.object(ocr, "find_tesseract", side_effect=ocr.OcrError("Engine unavailable")):
            with self.assertRaises(ocr.OcrError):
                ocr.recognize_flagged_pages(self.document, self.data)
        self.assertFalse(self.document.passages[1].ocr_attempted)

    def test_no_flagged_pages_does_not_start_engine(self) -> None:
        data = pdf_bytes(["Native"])
        document = processing.process_document("native.pdf", data)
        with patch.object(ocr, "find_tesseract") as find:
            result = ocr.recognize_flagged_pages(document, data)
            self.assertEqual(result, document)
            find.assert_not_called()

    def test_tesseract_receives_pipes_not_file_paths(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout=b"Text", stderr=b"")
        with patch.object(ocr.subprocess, "run", return_value=completed) as run:
            text = ocr._recognize_image("engine.exe", b"PNG DATA", 300, 10)
        self.assertEqual(text, "Text")
        self.assertEqual(run.call_args.args[0][:3], ["engine.exe", "stdin", "stdout"])
        self.assertEqual(run.call_args.kwargs["input"], b"PNG DATA")
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.kwargs["timeout"], 10)

    def test_native_errors_are_not_exposed(self) -> None:
        result = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"CONFIDENTIAL_SENTINEL")
        with patch.object(ocr, "_run", return_value=result):
            with self.assertRaises(ocr.OcrError) as error:
                ocr._recognize_image("engine", b"image", 300, 1)
        self.assertNotIn("CONFIDENTIAL_SENTINEL", str(error.exception))

    def test_total_deadline_stops_new_page_work(self) -> None:
        with (
            patch.object(ocr, "find_tesseract", return_value="engine"),
            patch.object(ocr, "verify_tesseract"),
            patch.object(ocr.time, "monotonic", side_effect=[0, 121]),
            patch.object(ocr, "_render_page") as render,
        ):
            result = ocr.recognize_flagged_pages(self.document, self.data)
        render.assert_not_called()
        self.assertFalse(result.passages[1].ocr_attempted)

    def test_first_lines_are_development_only_and_include_blank_pages(self) -> None:
        settings = settings_module.DocumentSettings(environment="development", enable_first_lines=True)
        lines = settings_module.development_first_lines(self.document, settings)
        self.assertEqual([location for location, line in lines], ["Page 1", "Page 2", "Page 3"])
        self.assertIn("Native page", lines[0][1])
        self.assertIn("No readable text", lines[1][1])
        self.assertFalse(settings_module.development_first_lines(
            self.document, replace(settings, environment="production")))
        self.assertFalse(settings_module.development_first_lines(self.document, settings_module.DocumentSettings()))

    def test_first_line_never_invents_docx_or_txt_pages(self) -> None:
        document = processing.process_document("policy.txt", b"First line\nSecond line")
        settings = settings_module.DocumentSettings(environment="development", enable_first_lines=True)
        lines = settings_module.development_first_lines(document, settings)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0][0], "Line 1")


class LocalOcrIntegrationTest(unittest.TestCase):
    def test_real_rendering_and_english_ocr_with_native_and_blank_pages(self) -> None:
        try:
            engine = ocr.find_tesseract()
        except ocr.OcrError:
            self.skipTest("Tesseract not installed; mocked OCR tests still run.")
        ocr.verify_tesseract(engine)
        writer = PdfWriter()
        writer.append(BytesIO(pdf_bytes(["Native policy retained"])))
        writer.append(BytesIO(scanned_pdf()))
        writer.add_blank_page(width=300, height=300)
        output = BytesIO()
        writer.write(output)
        data = output.getvalue()
        document = processing.process_document("synthetic-ocr.pdf", data)
        self.assertTrue(document.passages[1].may_require_ocr)
        result = ocr.recognize_flagged_pages(document, data)
        self.assertEqual(result.passages[0], document.passages[0])
        self.assertIn("SYNTHETIC POLICY PAGE", result.passages[1].text.upper())
        self.assertIn("databases private", result.passages[1].text.lower())
        self.assertEqual(result.passages[1].extraction_method, "ocr")
        self.assertTrue(result.passages[2].may_require_ocr)
        self.assertTrue(result.passages[2].ocr_attempted)

    def test_renderer_rejects_oversized_page_before_rasterizing(self) -> None:
        writer = PdfWriter()
        writer.add_blank_page(width=10000, height=10000)
        output = BytesIO()
        writer.write(output)
        with self.assertRaisesRegex(ocr.OcrError, "pixel limit"):
            ocr._render_page(output.getvalue(), 1, ocr.OcrLimits(), 30)

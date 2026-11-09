"""Synthetic documents are generated in memory; no policy fixtures on disk."""

from contextlib import redirect_stderr
from io import BytesIO, StringIO
import importlib
import logging
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile

from docx import Document
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))
try:
    processing = importlib.import_module("architecture_review.document_processing")
    settings_module = importlib.import_module("architecture_review.document_settings")
finally:
    sys.path.pop(0)


def pdf_bytes(texts: list[str | None], encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=300, height=300)
        if text is not None:
            font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                     NameObject("/Subtype"): NameObject("/Type1"),
                                     NameObject("/BaseFont"): NameObject("/Helvetica")})
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)}),
            })
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 20 200 Td ({text}) Tj ET".encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("synthetic-password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def docx_bytes(with_content: bool = True) -> bytes:
    document = Document()
    if with_content:
        document.add_paragraph("Synthetic security policy")
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Control"
        table.cell(0, 1).text = "Restrict database access"
        document.add_paragraph("Synthetic recovery policy")
    output = BytesIO()
    document.save(output)
    return output.getvalue()


class ExtractionTest(unittest.TestCase):
    def test_pdf_text_and_original_filename(self) -> None:
        document = processing.process_document("Company Policy.PDF", pdf_bytes(["Private databases only"]))
        self.assertEqual(document.filename, "Company Policy.PDF")
        self.assertEqual(document.format, "pdf")
        self.assertEqual(document.status, "readable")
        self.assertIn("Private databases", document.passages[0].text)
        self.assertEqual(document.passages[0].page_number, 1)

    def test_multi_page_pdf_preserves_page_numbers(self) -> None:
        document = processing.process_document("policy.pdf", pdf_bytes(["Page one", "Page two"]))
        self.assertEqual([part.page_number for part in document.passages], [1, 2])

    def test_blank_pdf_is_not_assumed_scanned(self) -> None:
        document = processing.process_document("blank.pdf", pdf_bytes([None]))
        self.assertEqual(document.status, "unreadable")
        self.assertTrue(document.passages[0].may_require_ocr)
        self.assertIn("blank", document.passages[0].warnings[0])

    def test_image_only_pdf_needs_review(self) -> None:
        output = BytesIO()
        Image.new("RGB", (100, 100), "white").save(output, format="PDF")
        document = processing.process_document("scan.pdf", output.getvalue())
        self.assertTrue(document.requires_further_processing)
        self.assertTrue(document.passages[0].may_require_ocr)
        self.assertEqual(document.passages[0].page_number, 1)

    def test_mixed_pdf_keeps_unreadable_pages(self) -> None:
        document = processing.process_document("mixed.pdf", pdf_bytes(["Readable", None, "Also readable"]))
        self.assertEqual(document.status, "needs_processing")
        self.assertEqual(len(document.passages), 3)
        self.assertEqual(document.passages[1].page_number, 2)
        self.assertTrue(document.passages[1].may_require_ocr)
        self.assertFalse(document.passages[0].may_require_ocr)

    def test_docx_paragraphs_and_tables_in_order(self) -> None:
        document = processing.process_document("policy.docx", docx_bytes())
        self.assertEqual([part.text for part in document.passages], [
            "Synthetic security policy", "Control", "Restrict database access", "Synthetic recovery policy",
        ])
        self.assertIn("Table 1, row 1, cell 2", document.passages[2].location)
        self.assertTrue(all(part.page_number is None for part in document.passages))

    def test_txt_utf8_bom_and_line_locations(self) -> None:
        document = processing.process_document("policy.txt", "\ufeffSecurity policy\n\nCafé access".encode())
        self.assertEqual(document.format, "txt")
        self.assertEqual([part.location for part in document.passages], ["Line 1", "Line 3"])
        self.assertEqual(document.passages[1].text, "Café access")

    def test_empty_documents(self) -> None:
        with self.assertRaisesRegex(processing.DocumentProcessingError, "empty"):
            processing.process_document("empty.txt", b"")
        for name, content in (("blank.txt", b" \n\t"), ("blank.docx", docx_bytes(False)), ("empty.pdf", pdf_bytes([]))):
            with self.subTest(name=name):
                document = processing.process_document(name, content)
                self.assertEqual(document.status, "unreadable")
                self.assertTrue(document.warnings)

    def test_unsupported_and_mismatched_content(self) -> None:
        for name, content in (("old.doc", b"legacy"), ("bad.exe", b"MZ"),
                              ("fake.pdf", b"text"), ("fake.docx", b"text"),
                              ("renamed.txt", pdf_bytes(["secret"])), ("binary.txt", b"a\x00b")):
            with self.subTest(name=name), self.assertRaises(processing.DocumentProcessingError):
                processing.process_document(name, content)

    def test_invalid_utf8(self) -> None:
        with self.assertRaisesRegex(processing.DocumentProcessingError, "UTF-8"):
            processing.process_document("policy.txt", b"\xff\xfeinvalid")

    def test_corruption_and_encryption_errors_are_safe(self) -> None:
        for name, content in (("broken.pdf", b"%PDF-1.7\nCONFIDENTIAL_SENTINEL"),
                              ("broken.docx", b"PK\x03\x04CONFIDENTIAL_SENTINEL"),
                              ("locked.pdf", pdf_bytes(["CONFIDENTIAL_SENTINEL"], encrypted=True))):
            with self.subTest(name=name):
                captured = StringIO()
                handler = logging.StreamHandler(captured)
                logging.getLogger().addHandler(handler)
                try:
                    with redirect_stderr(captured), self.assertRaises(processing.DocumentProcessingError) as error:
                        processing.process_document(name, content)
                finally:
                    logging.getLogger().removeHandler(handler)
                self.assertNotIn("CONFIDENTIAL_SENTINEL", str(error.exception))
                self.assertNotIn("CONFIDENTIAL_SENTINEL", captured.getvalue())

    def test_zip_is_not_automatically_docx(self) -> None:
        output = BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("data.txt", "not Word")
        with self.assertRaises(processing.DocumentProcessingError):
            processing.process_document("fake.docx", output.getvalue())

    def test_limits(self) -> None:
        cases = [
            ("policy.txt", b"12345", processing.ProcessingLimits(max_upload_bytes=4)),
            ("policy.pdf", pdf_bytes(["one", "two"]), processing.ProcessingLimits(max_pdf_pages=1)),
            ("policy.txt", b"12345", processing.ProcessingLimits(max_text_chars=4)),
            ("policy.txt", b"one\ntwo", processing.ProcessingLimits(max_passages=1)),
            ("policy.docx", docx_bytes(), processing.ProcessingLimits(max_expanded_bytes=100)),
            ("policy.docx", docx_bytes(), processing.ProcessingLimits(max_docx_entries=1)),
        ]
        for name, data, limits in cases:
            with self.subTest(name=name, limits=limits), self.assertRaises(processing.DocumentProcessingError):
                processing.process_document(name, data, limits)

    def test_nested_docx_table_location(self) -> None:
        document = Document()
        table = document.add_table(rows=1, cols=1)
        nested = table.cell(0, 0).add_table(rows=1, cols=1)
        nested.cell(0, 0).text = "Nested control"
        output = BytesIO()
        document.save(output)
        result = processing.process_document("nested.docx", output.getvalue())
        self.assertEqual(result.passages[0].text, "Nested control")
        self.assertIn("Table 1, row 1, cell 1, Table 1", result.passages[0].location)

    def test_page_decode_failure_keeps_page_reference(self) -> None:
        from types import SimpleNamespace
        from unittest.mock import Mock
        failed_page = Mock()
        failed_page.get_contents.side_effect = RuntimeError("CONFIDENTIAL_SENTINEL")
        fake_reader = SimpleNamespace(is_encrypted=False, pages=[failed_page])
        with patch.object(processing, "PdfReader", return_value=fake_reader):
            document = processing.process_document("badpage.pdf", b"%PDF-1.7")
        self.assertEqual(document.passages[0].page_number, 1)
        self.assertEqual(document.passages[0].status, "unreadable")
        self.assertNotIn("CONFIDENTIAL_SENTINEL", str(document.passages[0].warnings))

    def test_text_excluded_from_repr(self) -> None:
        document = processing.process_document("policy.txt", b"CONFIDENTIAL_SENTINEL")
        self.assertNotIn("CONFIDENTIAL_SENTINEL", repr(document))
        self.assertNotIn("CONFIDENTIAL_SENTINEL", repr(document.passages[0]))


class DocumentSettingsTest(unittest.TestCase):
    def test_upload_limit_environment_configuration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(settings_module.load_document_settings().upload_limit_mb, 10)
        with patch.dict(os.environ, {"POLICY_MAX_UPLOAD_MB": "2"}, clear=True):
            self.assertEqual(settings_module.load_document_settings().limits.max_upload_bytes, 2 * 1024 * 1024)
        for value in ("zero", "0", "26"):
            with patch.dict(os.environ, {"POLICY_MAX_UPLOAD_MB": value}), self.assertRaises(ValueError):
                settings_module.load_document_settings()

"""Local, in-memory policy extraction. No network calls or disk persistence."""

from dataclasses import dataclass, field
from io import BytesIO
import hashlib
import logging
from pathlib import PurePosixPath
from typing import Literal, cast
import zipfile

from docx import Document
from docx.document import Document as DocumentObject
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from pypdf import PdfReader


Status = Literal["readable", "needs_processing", "unreadable"]
Format = Literal["pdf", "docx", "txt"]
UNREADABLE_PAGE = (
    "No usable text was extracted. This page may be scanned, blank or unsupported; "
    "text recognition or manual review may be needed."
)


class DocumentProcessingError(ValueError):
    """A safe user-facing message without document text or parser details."""


@dataclass(frozen=True)
class ProcessingLimits:
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pdf_pages: int = 200
    max_docx_entries: int = 2000
    max_expanded_bytes: int = 30 * 1024 * 1024
    max_text_chars: int = 1_000_000
    max_passages: int = 20_000

    def __post_init__(self) -> None:
        if any(type(value) is not int or value < 1 for value in vars(self).values()):
            raise ValueError("Processing limits must be positive integers.")


@dataclass(frozen=True)
class Passage:
    """A page, paragraph, table cell or TXT line with source location."""

    text: str = field(repr=False)
    location: str
    status: Status
    page_number: int | None = None
    may_require_ocr: bool = False
    warnings: tuple[str, ...] = ()
    extraction_method: Literal["native", "ocr"] = "native"
    ocr_attempted: bool = False


@dataclass(frozen=True)
class ProcessedDocument:
    """One policy and its passages, retained only in the caller's memory."""

    filename: str
    format: Format
    passages: tuple[Passage, ...] = field(repr=False)
    status: Status
    warnings: tuple[str, ...] = ()
    source_sha256: str = ""

    @property
    def requires_further_processing(self) -> bool:
        return self.status != "readable"


class _PrivateParserLogs(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # pypdf diagnostics can contain fragments of a malformed document.
        return False


# Do not let third-party PDF parser diagnostics disclose uploaded content.
for _name in list(logging.Logger.manager.loggerDict):
    if _name == "pypdf" or _name.startswith("pypdf."):
        logging.getLogger(_name).addFilter(_PrivateParserLogs())


def _usable(text: str) -> bool:
    return any(character.isalnum() for character in text)


def _check_total(passages: list[Passage], limits: ProcessingLimits) -> None:
    if len(passages) > limits.max_passages:
        raise DocumentProcessingError("Document contains too many passages to process locally.")
    if sum(len(passage.text) for passage in passages) > limits.max_text_chars:
        raise DocumentProcessingError("Extracted text exceeds the local processing limit.")


def _append_passage(passages: list[Passage], passage: Passage, total: int, limits: ProcessingLimits) -> int:
    """Check running limits before retaining another passage."""
    total += len(passage.text)
    if total > limits.max_text_chars or len(passages) >= limits.max_passages:
        raise DocumentProcessingError("Document exceeds the local text or passage processing limit.")
    passages.append(passage)
    return total


def _pdf(data: bytes, limits: ProcessingLimits) -> list[Passage]:
    if not data.startswith(b"%PDF-"):
        raise DocumentProcessingError("File content is not a PDF document.")
    reader = PdfReader(BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise DocumentProcessingError("Encrypted PDFs are not supported. Upload an unencrypted copy.")
    if len(reader.pages) > limits.max_pdf_pages:
        raise DocumentProcessingError("PDF exceeds the configured page limit.")
    passages = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            stream = page.get_contents()
            if stream is not None and len(stream.get_data()) > limits.max_expanded_bytes:
                raise DocumentProcessingError("PDF page content exceeds the local processing limit.")
            text = page.extract_text() or ""
            readable = _usable(text)
            passages.append(Passage(
                text=text, location=f"Page {number}", page_number=number,
                status="readable" if readable else "unreadable",
                may_require_ocr=not readable,
                warnings=() if readable else (UNREADABLE_PAGE,),
            ))
        except DocumentProcessingError:
            raise
        except Exception:
            passages.append(Passage(
                text="", location=f"Page {number}", page_number=number,
                status="unreadable", may_require_ocr=True,
                warnings=("This page could not be decoded. Manual review or text recognition may be needed.",),
            ))
        _check_total(passages, limits)
    return passages


def _docx(data: bytes, limits: ProcessingLimits) -> list[Passage]:
    if not zipfile.is_zipfile(BytesIO(data)):
        raise DocumentProcessingError("File content is not a DOCX document. Encrypted Word files are not supported.")
    with zipfile.ZipFile(BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > limits.max_docx_entries or sum(item.file_size for item in entries) > limits.max_expanded_bytes:
            raise DocumentProcessingError("DOCX archive exceeds the local processing limit.")
        if any(item.flag_bits & 1 for item in entries):
            raise DocumentProcessingError("Encrypted Word files are not supported.")
        if not {"[Content_Types].xml", "word/document.xml"}.issubset(archive.namelist()):
            raise DocumentProcessingError("File content is not a Word DOCX document.")
        if any(item.filename.lower().endswith("vbaproject.bin") for item in entries):
            raise DocumentProcessingError("Macro-enabled Word documents are not supported.")
    document = Document(BytesIO(data))
    passages: list[Passage] = []
    total = 0

    def walk(container: DocumentObject | _Cell, prefix: str = "") -> None:
        nonlocal total
        paragraph_number = table_number = 0
        for block in container.iter_inner_content():
            if isinstance(block, Paragraph):
                paragraph_number += 1
                text = block.text
                if _usable(text):
                    total = _append_passage(passages, Passage(
                        text=text, location=f"{prefix}Paragraph {paragraph_number}", status="readable",
                    ), total, limits)
            elif isinstance(block, Table):
                table_number += 1
                seen = set()
                for row_number, row in enumerate(block.rows, start=1):
                    for column_number, cell in enumerate(row.cells, start=1):
                        # Merged cells can be repeated by the Word API.
                        if cell._tc in seen:
                            continue
                        seen.add(cell._tc)
                        walk(cell, f"{prefix}Table {table_number}, row {row_number}, cell {column_number}, ")

    walk(document)
    return passages


def _txt(data: bytes, limits: ProcessingLimits) -> list[Passage]:
    if data.startswith((b"%PDF-", b"PK\x03\x04", b"\xd0\xcf\x11\xe0")):
        raise DocumentProcessingError("File content does not match plain text.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise DocumentProcessingError("Text files must use UTF-8 encoding. Re-save as UTF-8 and try again.") from None
    if any(ord(character) < 32 and character not in "\t\n\r\f" for character in text):
        raise DocumentProcessingError("File contains binary or unsupported control characters.")
    if len(text) > limits.max_text_chars:
        raise DocumentProcessingError("Extracted text exceeds the local processing limit.")
    passages: list[Passage] = []
    total = 0
    for number, line in enumerate(text.splitlines(), start=1):
        if _usable(line):
            total = _append_passage(passages, Passage(
                text=line, location=f"Line {number}", status="readable",
            ), total, limits)
    return passages


def process_document(filename: str, data: bytes, limits: ProcessingLimits | None = None) -> ProcessedDocument:
    """Validate and extract a single uploaded file without persisting its bytes."""
    limits = limits or ProcessingLimits()
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        raise DocumentProcessingError("Supported formats are PDF, DOCX and UTF-8 TXT. Legacy DOC is not supported.")
    if len(data) > limits.max_upload_bytes:
        raise DocumentProcessingError("File exceeds the configured upload size limit.")
    if not data:
        raise DocumentProcessingError("The uploaded file is empty.")
    format_name = cast(Format, suffix[1:])
    try:
        passages = {"pdf": _pdf, "docx": _docx, "txt": _txt}[format_name](data, limits)
    except DocumentProcessingError:
        raise
    except Exception:
        raise DocumentProcessingError("Document could not be read. It may be corrupted, encrypted or unsupported.") from None
    readable = sum(passage.status == "readable" for passage in passages)
    status: Status = "readable" if passages and readable == len(passages) else "needs_processing" if readable else "unreadable"
    warnings = () if status == "readable" else (
        "Some content could not be read. Review the listed locations before using this document for assessment."
        if readable else "No usable text was extracted. This document needs further processing or manual review.",
    )
    if format_name == "docx":
        warnings += ("Extracted main-body paragraphs and tables only. Headers, footers, text boxes, images and tracked changes may need manual review; Word page numbers are not available.",)
    return ProcessedDocument(filename=filename, format=format_name, passages=tuple(passages), status=status, warnings=warnings,
                             source_sha256=hashlib.sha256(data).hexdigest())

"""Bounded local Tesseract OCR using pipes, without temporary document files."""

from dataclasses import dataclass, replace
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from architecture_review.document_processing import ProcessedDocument, ProcessingLimits


class OcrError(ValueError):
    """Safe OCR message without document text or native diagnostics."""


@dataclass(frozen=True)
class OcrLimits:
    max_pages: int = 5
    dpi: int = 300
    max_pixels: int = 12_000_000
    page_timeout: float = 30
    render_timeout: float = 30
    total_timeout: float = 120

    def __post_init__(self) -> None:
        if (type(self.max_pages) is not int or not 1 <= self.max_pages <= 5
                or type(self.dpi) is not int or not 72 <= self.dpi <= 300
                or type(self.max_pixels) is not int or not 1 <= self.max_pixels <= 12_000_000
                or not all(0 < value <= 120 for value in (self.page_timeout, self.render_timeout, self.total_timeout))):
            raise ValueError("Invalid OCR processing limits.")


def _run(arguments: list[str], data: bytes = b"", timeout: float = 5) -> subprocess.CompletedProcess:
    """Run one owned child; subprocess.run kills/waits for it on timeout."""
    return subprocess.run(
        arguments, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout, check=False, shell=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        cwd=str(Path(__file__).resolve().parents[1]),
    )


def find_tesseract() -> str:
    """Locate a configured engine without changing PATH or system settings."""
    configured = os.environ.get("TESSERACT_CMD")
    if configured:
        if Path(configured).is_absolute() and Path(configured).is_file():
            return configured
        raise OcrError("TESSERACT_CMD must point to an existing Tesseract executable.")
    executable = shutil.which("tesseract")
    if executable:
        return executable
    candidates = [Path(os.environ.get(key, fallback)) / "Tesseract-OCR" / "tesseract.exe"
                  for key, fallback in (("ProgramFiles", "C:/Program Files"), ("ProgramFiles(x86)", "C:/Program Files (x86)"))]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise OcrError("Tesseract is not installed or could not be found. See the local development instructions.")


def verify_tesseract(executable: str) -> None:
    try:
        result = _run([executable, "--list-langs"])
    except (OSError, subprocess.TimeoutExpired):
        raise OcrError("Tesseract could not be started. Check the local OCR installation.") from None
    if result.returncode or "eng" not in result.stdout.decode("utf-8", errors="replace").splitlines():
        raise OcrError("Tesseract English language data is unavailable. Install the eng language data.")


def _render_page(data: bytes, number: int, limits: OcrLimits, timeout: float) -> bytes:
    result = _run([
        sys.executable, "-B", "-m", "architecture_review.ocr_render",
        str(number), str(limits.dpi), str(limits.max_pixels),
    ], data, timeout)
    if result.returncode == 3:
        raise OcrError("Page image exceeds the OCR pixel limit and needs manual review.")
    if result.returncode or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        raise OcrError("Page could not be rendered for text recognition.")
    return result.stdout


def _recognize_image(executable: str, image: bytes, dpi: int, timeout: float) -> str:
    result = _run([executable, "stdin", "stdout", "-l", "eng", "--dpi", str(dpi), "--psm", "3"], image, timeout)
    if result.returncode:
        raise OcrError("Text recognition failed for this page. Manual review may be needed.")
    try:
        return result.stdout.decode("utf-8").strip()
    except UnicodeDecodeError:
        raise OcrError("Text recognition returned unsupported text encoding.") from None


def recognize_flagged_pages(document: ProcessedDocument, data: bytes, limits: OcrLimits | None = None) -> ProcessedDocument:
    """Attempt untried unreadable pages; preserve native text and failed references."""
    limits = limits or OcrLimits()
    if document.format != "pdf":
        raise OcrError("Text recognition is available for PDF documents only.")
    if len(data) > 25 * 1024 * 1024 or not data.startswith(b"%PDF-"):
        raise OcrError("The original PDF is unavailable or exceeds the OCR upload limit.")
    if document.source_sha256 != hashlib.sha256(data).hexdigest():
        raise OcrError("The uploaded PDF has changed. Re-upload it before text recognition.")
    eligible = [part for part in document.passages if part.may_require_ocr and not part.ocr_attempted]
    if not eligible:
        return document
    started = time.monotonic()
    executable = find_tesseract()
    verify_tesseract(executable)
    passages = list(document.passages)
    selected = {part.page_number for part in eligible[:limits.max_pages]}
    retained_chars = sum(len(part.text) for part in passages)

    for index, part in enumerate(passages):
        if part.page_number not in selected:
            continue
        remaining = limits.total_timeout - (time.monotonic() - started)
        if remaining <= 0:
            break
        try:
            image = _render_page(data, part.page_number, limits, min(limits.render_timeout, remaining))
            remaining = limits.total_timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise OcrError("The OCR time budget was reached. Manual review is needed.")
            text = _recognize_image(executable, image, limits.dpi, min(limits.page_timeout, remaining))
            if not any(character.isalnum() for character in text):
                raise OcrError("No usable text was recognised. The page may be blank or need manual review.")
            proposed_chars = retained_chars + len(text) - len(part.text)
            if proposed_chars > ProcessingLimits().max_text_chars:
                raise OcrError("OCR text exceeds the local text limit. Manual review is needed.")
            retained_chars = proposed_chars
            passages[index] = replace(
                part, text=text, status="readable", may_require_ocr=False,
                extraction_method="ocr", ocr_attempted=True,
                warnings=("OCR-derived text may contain errors and needs manual verification.",),
            )
        except subprocess.TimeoutExpired:
            passages[index] = replace(part, ocr_attempted=True, warnings=("Text recognition or rendering timed out. Manual review is needed.",))
        except (OcrError, OSError) as error:
            message = str(error) if isinstance(error, OcrError) else "Local text recognition could not start."
            passages[index] = replace(part, ocr_attempted=True, warnings=(message,))

    has_text = any(part.status == "readable" for part in passages)
    untried = sum(part.may_require_ocr and not part.ocr_attempted for part in passages)
    warnings = ["Text recognition was attempted locally. OCR-derived text needs manual verification; unresolved pages remain flagged."]
    if untried:
        warnings.append(f"{untried} flagged page(s) were not attempted within the automatic page/time limits. Upload smaller PDFs or review those pages manually.")
    return replace(document, passages=tuple(passages), status="needs_processing" if has_text else "unreadable", warnings=tuple(warnings))

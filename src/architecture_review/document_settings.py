"""Explicit local policy-upload settings; previews fail closed."""

from dataclasses import dataclass
import os

from architecture_review.document_processing import ProcessedDocument, ProcessingLimits


@dataclass(frozen=True)
class DocumentSettings:
    upload_limit_mb: int = 10
    environment: str = "production"
    enable_preview: bool = False
    enable_first_lines: bool = False

    def __post_init__(self) -> None:
        if type(self.upload_limit_mb) is not int or not 1 <= self.upload_limit_mb <= 25:
            raise ValueError("POLICY_MAX_UPLOAD_MB must be an integer from 1 to 25.")

    @property
    def preview_allowed(self) -> bool:
        return self.environment == "development" and self.enable_preview is True

    @property
    def first_lines_allowed(self) -> bool:
        return self.environment == "development" and self.enable_first_lines is True

    @property
    def limits(self) -> ProcessingLimits:
        return ProcessingLimits(max_upload_bytes=self.upload_limit_mb * 1024 * 1024)


def load_document_settings() -> DocumentSettings:
    """Read configuration without creating files or changing the environment."""
    try:
        size = int(os.environ.get("POLICY_MAX_UPLOAD_MB", "10"))
    except ValueError:
        raise ValueError("POLICY_MAX_UPLOAD_MB must be an integer from 1 to 25.") from None
    return DocumentSettings(
        upload_limit_mb=size,
        environment=os.environ.get("APP_ENV", "production").strip().lower(),
        enable_preview=os.environ.get("POLICY_DEV_PREVIEW", "false").strip().lower() == "true",
        enable_first_lines=os.environ.get("POLICY_DEV_FIRST_LINES", "false").strip().lower() == "true",
    )


def development_preview(document: ProcessedDocument, settings: DocumentSettings) -> str | None:
    """Return at most 500 characters, and never the entire extracted document."""
    if not settings.preview_allowed:
        return None
    total = sum(len(passage.text) for passage in document.passages)
    length = min(500, total // 2)
    if not length:
        return None
    parts = []
    remaining = length
    for passage in document.passages:
        excerpt = passage.text[:remaining]
        parts.append(excerpt)
        remaining -= len(excerpt)
        if not remaining:
            break
    return "".join(parts) + "…"


def development_first_lines(document: ProcessedDocument, settings: DocumentSettings) -> tuple[tuple[str, str], ...]:
    """Temporary visual check: two nonempty lines per PDF page or document."""
    if not settings.first_lines_allowed:
        return ()
    passages = document.passages
    lines = []
    for passage in passages:
        extracted = [line.strip() for line in passage.text.splitlines() if line.strip()][:2]
        if document.format != "pdf":
            extracted = []
            for part in passages:
                extracted.extend(line.strip() for line in part.text.splitlines() if line.strip())
                if len(extracted) >= 2:
                    break
            extracted = extracted[:2]
        first = "\n".join(line[:200] + ("…" if len(line) > 200 else "") for line in extracted)
        first = first or "[No readable text extracted — manual review may be needed]"
        method = "OCR" if passage.extraction_method == "ocr" else "native extraction"
        lines.append((passage.location, f"{first} ({method})"))
        if document.format != "pdf":
            break
    return tuple(lines)

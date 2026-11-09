"""Local policy-upload size configuration."""

from dataclasses import dataclass
import os

from architecture_review.document_processing import ProcessingLimits


@dataclass(frozen=True)
class DocumentSettings:
    upload_limit_mb: int = 10

    def __post_init__(self) -> None:
        if type(self.upload_limit_mb) is not int or not 1 <= self.upload_limit_mb <= 25:
            raise ValueError("POLICY_MAX_UPLOAD_MB must be an integer from 1 to 25.")

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
    )

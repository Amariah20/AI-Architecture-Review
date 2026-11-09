"""Session-only multi-policy uploads and compact document rows."""

from dataclasses import dataclass, field
import hashlib
from html import escape

import streamlit as st

from architecture_review.document_processing import DocumentProcessingError, ProcessedDocument, process_document
from architecture_review.document_settings import load_document_settings
from architecture_review.ocr import OcrError, recognize_flagged_pages


MAX_DOCUMENTS = 10
MAX_SESSION_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class PolicyUpload:
    id: str
    filename: str
    size: int
    document: ProcessedDocument | None = field(default=None, repr=False)
    error: str | None = None
    ocr_error: str | None = None

    @property
    def needs_review(self) -> bool:
        return bool(self.error or self.ocr_error or self.document is None
                    or self.document.requires_further_processing or self.document.warnings)


def process_upload(filename: str, data: bytes) -> PolicyUpload:
    """Reuse native extraction and automatic OCR; retain no original bytes."""
    identifier = hashlib.sha256(filename.encode("utf-8") + b"\0" + data).hexdigest()
    document = None
    error = ocr_error = None
    try:
        document = process_document(filename, data, load_document_settings().limits)
        if document.format == "pdf" and any(part.may_require_ocr and not part.ocr_attempted for part in document.passages):
            try:
                document = recognize_flagged_pages(document, data)
            except OcrError as problem:
                ocr_error = str(problem)
            except Exception:
                ocr_error = "Text recognition failed. Existing extracted text has been preserved."
    except DocumentProcessingError as problem:
        error = str(problem)
    except Exception:
        error = "Policy processing failed. Please try a different supported document."
    return PolicyUpload(identifier, filename, len(data), document, error, ocr_error)


def clear_policy() -> None:
    """Remove all extracted content and reset the uploader's raw-file widget."""
    st.session_state["policy_documents"] = {}
    st.session_state["policy_seen_uploads"] = set()
    st.session_state["policy_upload_generation"] += 1
    st.session_state.pop("policy_notice", None)


def remove_policy(identifier: str) -> None:
    documents = dict(st.session_state["policy_documents"])
    documents.pop(identifier, None)
    st.session_state["policy_documents"] = documents


def accept_uploads(uploads: list) -> bool:
    """Add newly selected files without replacing earlier session documents."""
    settings = load_document_settings()
    changed = False
    for upload in uploads:
        token = getattr(upload, "file_id", None) or (upload.name, upload.size, id(upload))
        if token in st.session_state["policy_seen_uploads"]:
            continue
        st.session_state["policy_seen_uploads"].add(token)
        documents = st.session_state["policy_documents"]
        if len(documents) >= MAX_DOCUMENTS or sum(item.size for item in documents.values()) + upload.size > MAX_SESSION_BYTES:
            st.session_state["policy_notice"] = "Session upload limit reached (10 documents / 50 MiB). Remove a document before adding more."
            changed = True
            continue
        if upload.size > settings.limits.max_upload_bytes:
            identifier = hashlib.sha256(f"oversize:{upload.name}:{upload.size}".encode()).hexdigest()
            record = PolicyUpload(identifier, upload.name, upload.size, error="File exceeds the configured upload size limit.")
        else:
            data = upload.getvalue()
            identifier = hashlib.sha256(upload.name.encode("utf-8") + b"\0" + data).hexdigest()
            if identifier in documents:
                st.session_state["policy_notice"] = "That exact filename and content are already uploaded; no duplicate was added."
                changed = True
                continue
            with st.spinner("Extracting policy text locally; scanned PDF pages may take longer..."):
                record = process_upload(upload.name, data)
        st.session_state["policy_documents"] = {**documents, record.id: record}
        changed = True
    if changed:
        st.session_state["policy_upload_generation"] += 1
    return changed


def render_upload_control() -> None:
    with st.popover("Upload policy document", icon=":material/add:"):
        st.caption("PDF, DOCX or UTF-8 TXT. Local extraction and OCR only; policy text is not used in AWS searches.")
        try:
            settings = load_document_settings()
        except ValueError:
            st.error("Upload configuration is invalid. POLICY_MAX_UPLOAD_MB must be between 1 and 25.")
            return
        uploads = st.file_uploader(
            "Add policy documents", type=["pdf", "docx", "txt"], accept_multiple_files=True,
            max_upload_size=settings.upload_limit_mb,
            key=f"policy_upload_{st.session_state['policy_upload_generation']}",
        )
        if uploads and accept_uploads(list(uploads)):
            st.rerun()
        if st.session_state.get("policy_notice"):
            st.caption(st.session_state["policy_notice"])


def render_policy_upload() -> None:
    """Show filenames, compact status and optional warnings, never policy text."""
    documents = st.session_state["policy_documents"]
    with st.container(key="policy_list"):
        heading, clear = st.columns([3, 1])
        heading.markdown(f"**Uploaded policy documents ({len(documents)})**")
        if documents:
            clear.button("Clear all", key="clear_policies", type="tertiary", on_click=clear_policy)
        else:
            st.caption("No policies uploaded. You can add documents one at a time.")
        names_seen: dict[str, int] = {}
        for identifier, record in documents.items():
            names_seen[record.filename] = names_seen.get(record.filename, 0) + 1
            variant = names_seen[record.filename]
            suffix = f" (document {variant} with this name)" if variant > 1 else ""
            with st.container(border=True):
                name, remove = st.columns([8, 1], vertical_alignment="center")
                file_type = record.filename.rsplit(".", 1)[-1].upper()
                with name:
                    st.markdown(f'<span class="document-type">{escape(file_type)}</span> '
                                f'<span class="policy-name">{escape(record.filename + suffix)}</span>', unsafe_allow_html=True)
                    status = "Could not extract text" if record.error else "Text extracted"
                    if record.document and record.document.status == "unreadable":
                        status = "No usable text"
                    if record.document and any(part.extraction_method == "ocr" for part in record.document.passages):
                        status = "Text extracted (OCR)"
                    failed = bool(record.error or record.ocr_error or (record.document and record.document.status == "unreadable"))
                    status_class = "policy-status-error" if failed else "policy-status-normal"
                    status_line = f'<span class="{status_class}">{escape(status)}</span>'
                    if record.ocr_error:
                        status_line += ' | <span class="policy-status-error">Text recognition failed</span>'
                    if record.needs_review:
                        status_line += ' | <span class="policy-status-warning">Manual review needed</span>'
                    st.markdown(f'<div class="policy-status">{record.size / 1024:.1f} KiB | {status_line}</div>', unsafe_allow_html=True)
                remove.button("", key=f"remove_policy_{identifier}", icon=":material/close:",
                              type="tertiary", help=f"Remove {record.filename}", on_click=remove_policy, args=(identifier,))
                if record.needs_review:
                    with st.expander("Processing details"):
                        if record.error:
                            st.error(record.error)
                        if record.ocr_error:
                            st.error(record.ocr_error)
                        if record.document:
                            for warning in record.document.warnings:
                                st.caption(warning)
                            for passage in record.document.passages:
                                if passage.may_require_ocr or passage.ocr_attempted:
                                    for warning in passage.warnings:
                                        st.caption(f"{passage.location}: {warning}")

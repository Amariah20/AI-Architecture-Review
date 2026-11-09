"""Streamlit policy upload UI; uploaded text is never used in MCP searches."""

import streamlit as st

from architecture_review.document_processing import DocumentProcessingError, process_document
from architecture_review.document_settings import development_preview, load_document_settings


def clear_policy() -> None:
    """Release the previous extracted policy when the upload changes/removes."""
    for key in ("policy_document", "policy_error", "policy_processed"):
        st.session_state.pop(key, None)


def render_policy_upload() -> None:
    """Process a single uploaded policy once and show metadata, not its text."""
    with st.expander("Company policy document", expanded=True):
        st.caption("Local extraction only. Documents stay in this application's memory and are not sent to AWS or included in searches. Use synthetic policies during development.")
        try:
            settings = load_document_settings()
        except ValueError:
            clear_policy()
            st.error("Policy upload configuration is invalid. POLICY_MAX_UPLOAD_MB must be between 1 and 25.")
            return

        upload = st.file_uploader(
            "Upload a policy (PDF, DOCX or UTF-8 TXT)",
            type=["pdf", "docx", "txt"],
            max_upload_size=settings.upload_limit_mb,
            key="policy_upload", on_change=clear_policy,
        )
        if upload is None:
            clear_policy()
            return

        st.text(f"Uploaded file: {upload.name}")
        if not st.session_state.get("policy_processed"):
            clear_policy()
            st.session_state["policy_processed"] = True
            try:
                if upload.size > settings.limits.max_upload_bytes:
                    raise DocumentProcessingError("File exceeds the configured upload size limit.")
                with st.spinner("Processing policy locally…"):
                    st.session_state["policy_document"] = process_document(
                        upload.name, upload.getvalue(), settings.limits,
                    )
            except DocumentProcessingError as error:
                st.session_state["policy_error"] = str(error)
            except Exception:
                st.session_state["policy_error"] = "Policy processing failed. Please try a different supported document."

        error = st.session_state.get("policy_error")
        if error:
            st.error(error)
            return
        document = st.session_state.get("policy_document")
        if document is None:
            return
        labels = {"readable": "Readable text extracted", "needs_processing": "Partially readable", "unreadable": "No usable text extracted"}
        st.text(f"Format: {document.format.upper()} | Status: {labels[document.status]}")
        st.text(f"Further processing required: {'Yes' if document.requires_further_processing else 'No'}")
        if document.status == "readable":
            st.success("Policy text extracted locally and held in this session for future integration.")
        for warning in document.warnings:
            st.warning(warning)
        unreadable = [passage for passage in document.passages if passage.may_require_ocr]
        if unreadable:
            st.warning("Some pages in this document could not be read automatically. They may contain scanned text or images, be blank, or use unsupported content. Additional text recognition or manual review may be needed before these pages can be included in your architecture assessment.")
            st.text("Locations to review: " + ", ".join(passage.location for passage in unreadable))
        preview = development_preview(document, settings)
        if preview is not None:
            with st.expander("Development-only extracted-text preview (limited)"):
                st.text(preview)

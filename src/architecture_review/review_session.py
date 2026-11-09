"""Session-only workspace state. No database, files or browser storage."""

from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from architecture_review.aws_documentation import DocumentationResult


@dataclass(frozen=True)
class ReviewEntry:
    id: str
    request: str = field(repr=False)
    sources: tuple[DocumentationResult, ...]
    policy_names: tuple[str, ...] = ()
    error: str | None = None


def initialise(state: MutableMapping[str, Any]) -> None:
    for key, value in {
        "workspace_view": "workspace", "review_history": [], "saved_sources": {},
        "policy_documents": {}, "policy_seen_uploads": set(), "policy_upload_generation": 0,
        "active_review_id": None, "result_page": 0,
    }.items():
        if key not in state:
            state[key] = value


def record_review(state: MutableMapping[str, Any], request: str,
                  sources: list[DocumentationResult], policy_names: tuple[str, ...],
                  error: str | None = None) -> ReviewEntry:
    unique_sources = {}
    for source in sources:
        unique_sources.setdefault(source.url.strip(), source)
    entry = ReviewEntry(uuid4().hex, request, tuple(unique_sources.values()), policy_names, error)
    state["review_history"] = [*state["review_history"], entry]
    state["active_review_id"] = entry.id
    state["result_page"] = 0
    return entry


def active_review(state: MutableMapping[str, Any]) -> ReviewEntry | None:
    return next((entry for entry in state["review_history"]
                 if entry.id == state["active_review_id"]), None)


def open_review(state: MutableMapping[str, Any], entry_id: str) -> None:
    entry = next(entry for entry in state["review_history"] if entry.id == entry_id)
    state["active_review_id"] = entry.id
    state["review_input"] = entry.request
    state["workspace_view"] = "workspace"
    state["result_page"] = 0
    state.pop("review_error", None)


def new_review(state: MutableMapping[str, Any]) -> None:
    """Clear this draft and policy content, retaining session history/bookmarks."""
    state["active_review_id"] = None
    state["review_input"] = ""
    state["workspace_view"] = "workspace"
    state["result_page"] = 0
    state["policy_documents"] = {}
    state["policy_seen_uploads"] = set()
    state["policy_upload_generation"] += 1
    state.pop("review_error", None)
    state.pop("policy_notice", None)


def toggle_saved_source(state: MutableMapping[str, Any], source: DocumentationResult) -> None:
    key = source.url.strip()
    saved = dict(state["saved_sources"])
    if key in saved:
        del saved[key]
    else:
        saved[key] = source
    state["saved_sources"] = saved

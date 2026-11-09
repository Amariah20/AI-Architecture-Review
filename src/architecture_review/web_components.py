"""Presentation helpers for sources, session navigation and viewer utilities."""

import hashlib
from html import escape
import re
from urllib.parse import urlsplit

import streamlit as st

from architecture_review.aws_documentation import DocumentationResult
from architecture_review.review_session import new_review, open_review, toggle_saved_source


BEDROCK_PLACEHOLDER = "To be populated when Amazon Bedrock is implemented."


def source_key(source: DocumentationResult) -> str:
    return hashlib.sha256(source.url.strip().encode()).hexdigest()[:16]


def safe_source_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return bool(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password)
    except ValueError:
        return False


def format_excerpt(text: str) -> str:
    """Preserve Markdown links, bold headings, and suppress remote images."""
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker.group(1)[0]
            elif marker.group(1)[0] == fence:
                fence = None
            lines.append(line)
        elif fence is not None:
            lines.append(line)
        else:
            line = re.sub(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", r"**\1**", line)
            lines.append(re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line))
    return "\n".join(lines)


def render_utilities() -> None:
    with st.container(key="utilities", horizontal=True, horizontal_alignment="right"):
        with st.popover("", icon=":material/info:", help="About this prototype"):
            st.markdown("**About this prototype**")
            st.write("Your submitted text retrieves AWS documentation. AI architecture reviews are not available yet.")
            st.write("Policies are processed locally, including OCR, but are not used in searches or reviews yet. Do not enter credentials.")
            st.write("History, uploads and saved sources are temporary.")


def _show_view(view: str) -> None:
    st.session_state["workspace_view"] = view


def render_sidebar() -> None:
    with st.sidebar, st.container(key="sidebar_layout"):
        st.markdown('<div class="workspace-brand">AWS Architecture<br>Review Assistant</div>', unsafe_allow_html=True)
        with st.container(key="sidebar_nav"):
            st.button("New review", key="nav_new", icon=":material/add:", width="stretch",
                      type="primary" if st.session_state["workspace_view"] == "workspace" else "secondary",
                      on_click=new_review, args=(st.session_state,))
            st.button("Session history", key="nav_history", icon=":material/history:", width="stretch",
                      type="primary" if st.session_state["workspace_view"] == "history" else "secondary",
                      on_click=_show_view, args=("history",))
            st.button("Saved sources", key="nav_saved", icon=":material/bookmark:", width="stretch",
                      type="primary" if st.session_state["workspace_view"] == "saved" else "secondary",
                      on_click=_show_view, args=("saved",))
        if st.session_state["saved_sources"]:
            st.caption(f"Saved sources ({len(st.session_state['saved_sources'])})")
            for source in st.session_state["saved_sources"].values():
                if safe_source_url(source.url):
                    st.link_button(source.title, source.url, width="stretch")
        with st.container(key="sidebar_footer"):
            st.divider()
            st.caption("Session-only data")
            st.caption("History and saved sources are temporary. New review clears the current inputs and uploaded policy content, while keeping this session's history and bookmarks.")


@st.dialog("Full retrieved excerpt", width="large")
def show_excerpt(source: DocumentationResult) -> None:
    st.subheader(source.title)
    st.markdown(format_excerpt(source.context), unsafe_allow_html=False)
    if safe_source_url(source.url):
        st.link_button("Open source", source.url, icon=":material/open_in_new:")


def render_source_card(source: DocumentationResult, scope: str = "result") -> None:
    identifier = source_key(source)
    saved = source.url.strip() in st.session_state["saved_sources"]
    with st.container(border=True, key=f"source_{scope}_{identifier}"):
        title, bookmark = st.columns([5, 1], vertical_alignment="top")
        title.markdown(f'<p class="source-title">{escape(source.title)}</p>', unsafe_allow_html=True)
        bookmark.button("", key=f"save_{scope}_{identifier}",
                        icon=":material/bookmark:" if saved else ":material/bookmark_add:",
                        type="tertiary", help="Remove saved source" if saved else "Save source for this session",
                        on_click=toggle_saved_source, args=(st.session_state, source))
        for label, style in (("Main takeaway", "takeaway"), ("Relevance", "relevance")):
            with st.container(key=f"detail_{scope}_{identifier}_{style}"):
                badge, value = st.columns([1, 6], gap="small")
                badge.markdown(f'<span class="result-label {style}">{label}</span>', unsafe_allow_html=True)
                value.write(BEDROCK_PLACEHOLDER)
        excerpt = source.context
        if len(excerpt) > 300:
            excerpt = excerpt[:300].rsplit(" ", 1)[0] + "…"
        with st.container(key=f"excerpt_{scope}_{identifier}"):
            badge, value = st.columns([1, 6], gap="small")
            badge.markdown('<span class="result-label">Source excerpt</span>', unsafe_allow_html=True)
            value.markdown(format_excerpt(excerpt), unsafe_allow_html=False)
        if re.search(r"\b(?:figure|fig\.|diagram|illustration)\s*\d*", source.context, re.IGNORECASE):
            st.caption("Open the source page to view referenced figures or diagrams.")
        with st.container(horizontal=True, horizontal_alignment="right", key=f"actions_{scope}_{identifier}"):
            if st.button("Full retrieved excerpt", key=f"excerpt_button_{scope}_{identifier}", icon=":material/article:"):
                show_excerpt(source)
            if safe_source_url(source.url):
                st.link_button("Open source", source.url, icon=":material/open_in_new:")


def render_history() -> None:
    st.header("Session history")
    st.caption("Revisit submitted text and its retrieved sources without searching again. History lasts only for this session.")
    if not st.session_state["review_history"]:
        st.info("No searches in this session yet. Start a new review to retrieve AWS guidance.")
    for index, entry in reversed(list(enumerate(st.session_state["review_history"], start=1))):
        with st.container(border=True):
            st.text(f"{index}. {entry.request[:140]}" + ("…" if len(entry.request) > 140 else ""))
            st.caption(f"{len(entry.sources)} retrieved sources" + (" · Retrieval failed" if entry.error else ""))
            st.button("Open search", key=f"history_{entry.id}", on_click=open_review, args=(st.session_state, entry.id))


def render_saved_sources() -> None:
    st.header("Saved sources")
    st.caption("Bookmarks are temporary and unique by source URL. Select the bookmark icon to remove a saved source.")
    if not st.session_state["saved_sources"]:
        st.info("No saved sources yet. Use the bookmark icon on an AWS documentation card.")
    with st.container(key="source_cards"):
        for source in list(st.session_state["saved_sources"].values()):
            render_source_card(source, scope="saved")

"""Local Streamlit interface for AWS documentation retrieval."""

import asyncio
import logging
import re
from urllib.parse import urlsplit

from PIL import Image
import streamlit as st

from architecture_review.aws_documentation import search_documentation


logger = logging.getLogger(__name__)
FETCH_LIMIT = 9
PAGE_SIZE = 3

PAGE_STYLES = """
<style>
[data-testid="stAppDeployButton"], [data-testid="stStatusWidget"] { display: none !important; }
.st-key-pagination {
    border: 1px solid rgba(128,128,128,0.22);
    border-radius: 999px;
    background: var(--secondary-background-color);
    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
    padding: 8px 16px;
    margin-top: 12px;
}
.st-key-pagination button {
    border: none; border-radius: 50%;
    min-width: 36px; width: 36px; height: 36px; min-height: 36px;
    padding: 0; background: transparent; color: var(--text-color, #777);
}
.st-key-pagination button p { color: inherit !important; }
.st-key-pagination button:disabled,
.st-key-pagination button:disabled:hover {
    opacity: 1; color: #888 !important; background: transparent;
    cursor: not-allowed;
}
.st-key-pagination button:focus-visible { outline: 2px solid #6478e8; outline-offset: 2px; }
.review-loading {
    position: fixed; inset: 0; z-index: 999999;
    display: flex; align-items: center; justify-content: center;
    background: rgba(128, 128, 128, 0.12);
}
.review-loading-card {
    background: var(--background-color, white); color: var(--text-color, #222);
    border-radius: 20px; padding: 32px 42px; text-align: center;
    box-shadow: 0 8px 40px rgba(0,0,0,0.12);
}
.review-loading-circle {
    width: 64px; height: 64px; margin: 0 auto 20px;
    border: 7px solid #ddd; border-top-color: #333;
    border-radius: 50%; animation: review-spin 0.9s linear infinite;
}
@keyframes review-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
    .review-loading-circle { animation-duration: 3s; }
}
</style>
"""

LOADING_OVERLAY = """
<div class="review-loading" role="status" aria-live="polite">
  <div class="review-loading-card">
    <div class="review-loading-circle" aria-hidden="true"></div>
    <strong>LOADING…</strong><br>Searching AWS documentation
  </div>
</div>
"""


def format_excerpt(text: str) -> str:
    """Use bold headings and Markdown links without loading remote images."""
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
            line = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", line)
            lines.append(line)
    return "\n".join(lines)


def change_page(page: int) -> None:
    """Change only the session's result page, without fetching again."""
    st.session_state.result_page = page


def retrieve_results(architecture: str, question: str) -> None:
    """Fetch once per submission and retain results only in this session."""
    if not architecture.strip() or not question.strip():
        st.error("Enter both an architecture description and a review question.")
        return

    query = f"{architecture.strip()}\n\nReview question: {question.strip()}"
    loading = st.empty()
    loading.markdown(LOADING_OVERLAY, unsafe_allow_html=True)
    try:
        results = asyncio.run(search_documentation(query, limit=FETCH_LIMIT))
    except TimeoutError:
        st.error("AWS documentation search timed out. Please try again shortly.")
        return
    except Exception:
        # Avoid exposing service responses or user input in the browser or logs.
        logger.warning("AWS documentation retrieval failed.")
        st.error("Could not retrieve AWS guidance. Check your internet connection and try again. The service may be temporarily unavailable or rate-limited.")
        return
    finally:
        loading.empty()

    if not results:
        st.warning("No documentation found. Try a more specific review question.")
        return

    st.session_state["documentation_results"] = results[:FETCH_LIMIT]


def main() -> None:
    """Collect a description and question, then display retrieved sources."""
    # A transparent icon leaves room for the user's future logo.
    st.set_page_config(page_title="AI Architecture Review", page_icon=Image.new("RGBA", (32, 32)))
    st.markdown(PAGE_STYLES, unsafe_allow_html=True)
    st.title("AI Architecture Review & Optimisation Assistant")
    st.caption("Explore AWS guidance for your architecture. Documentation retrieval only; automated reviews are not available yet.")
    st.info("Use synthetic examples only. Your description and question are sent to AWS documentation search. Do not enter credentials, private policies or company details.")

    with st.form("documentation_search"):
        architecture = st.text_area(
            "AWS architecture description",
            placeholder="A web application runs on EC2 and connects to an RDS MySQL database.",
            max_chars=10000,
        )
        question = st.text_input(
            "Review question",
            placeholder="What are the security risks of public database access?",
            max_chars=2000,
        )
        submitted = st.form_submit_button("Find AWS guidance")

    if submitted:
        # Clear earlier results even if the replacement search fails validation.
        st.session_state.pop("documentation_results", None)
        st.session_state["result_page"] = 0
        retrieve_results(architecture, question)

    results = st.session_state.get("documentation_results", [])
    if not results:
        return

    st.subheader("Retrieved AWS documentation")
    st.caption("These excerpts are source material, not a completed architecture assessment.")
    pages = (len(results) + PAGE_SIZE - 1) // PAGE_SIZE
    start = st.session_state.result_page * PAGE_SIZE
    for index, result in enumerate(results[start:start + PAGE_SIZE], start=start + 1):
        with st.container(border=True):
            st.text(f"{index}. {result.title}")
            st.markdown(format_excerpt(result.context), unsafe_allow_html=False)
            if re.search(r"\b(?:figure|fig\.|diagram|illustration)\s*\d*", result.context, re.IGNORECASE):
                st.caption("This excerpt refers to a figure or diagram. Open the source page to view it; images are not included in search excerpts.")
            url = urlsplit(result.url)
            if url.scheme == "https" and url.hostname and not url.username and not url.password:
                st.link_button("Open source", result.url)

    if pages > 1:
        # Widget keys give us a stable target without relying on internal button kinds.
        active_page = st.session_state.result_page
        st.markdown(f"""
        <style>
        .st-key-pagination .st-key-page_{active_page} button,
        .st-key-pagination .st-key-page_{active_page} button:hover,
        .st-key-pagination .st-key-page_{active_page} button:focus {{
            background: #4054b8 !important;
            color: #fff !important;
            border: 2px solid #9ba9ff !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.18);
        }}
        </style>
        """, unsafe_allow_html=True)
        st.caption(f"Page {st.session_state.result_page + 1} of {pages}")
        with st.container(key="pagination", horizontal=True, horizontal_alignment="center", vertical_alignment="center", gap="small"):
            st.button("‹", key="previous_page", help="Previous page",
                      disabled=st.session_state.result_page == 0,
                      on_click=change_page, args=(st.session_state.result_page - 1,))
            for page in range(pages):
                st.button(
                    str(page + 1), key=f"page_{page}", help=f"Go to page {page + 1}",
                    type="primary" if page == st.session_state.result_page else "secondary",
                    on_click=change_page, args=(page,),
                )
            st.button("›", key="next_page", help="Next page",
                      disabled=st.session_state.result_page == pages - 1,
                      on_click=change_page, args=(st.session_state.result_page + 1,))


if __name__ == "__main__":
    main()

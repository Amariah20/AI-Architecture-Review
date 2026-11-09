"""Responsive Streamlit workspace over the existing retrieval and extraction code."""

import asyncio
import logging

from PIL import Image
import streamlit as st

from architecture_review.web_styles import LOADING_OVERLAY, PAGE_STYLES


logger = logging.getLogger(__name__)
FETCH_LIMIT = 9
PAGE_SIZE = 3


def change_page(page: int) -> None:
    st.session_state["result_page"] = page


def retrieve_results(request: str, question: str | None = None) -> None:
    """Pass submitted text to MCP unchanged apart from outer whitespace."""
    from architecture_review.aws_documentation import search_documentation
    from architecture_review.review_session import record_review

    text = request.strip() if question is None else f"{request.strip()}\n\nReview question: {question.strip()}"
    st.session_state["active_review_id"] = None
    st.session_state.pop("review_error", None)
    if not request.strip() or (question is not None and not question.strip()):
        st.session_state["review_error"] = "Enter your architecture description and what you would like reviewed."
        return
    loading = st.empty()
    loading.markdown(LOADING_OVERLAY, unsafe_allow_html=True)
    error = None
    results = []
    try:
        results = asyncio.run(search_documentation(text, limit=FETCH_LIMIT))
    except TimeoutError:
        error = "AWS documentation search timed out. Please try again shortly."
    except Exception:
        logger.warning("AWS documentation retrieval failed.")
        error = "Could not retrieve AWS guidance. Check your internet connection and try again. The service may be temporarily unavailable or rate-limited."
    finally:
        loading.empty()
    names = tuple(record.filename for record in st.session_state["policy_documents"].values())
    record_review(st.session_state, text, results[:FETCH_LIMIT], names, error)


def render_results() -> None:
    from architecture_review.review_session import active_review
    from architecture_review.web_components import render_source_card

    st.header("Retrieved AWS documentation")
    st.caption("Documentation sources, not a completed AI architecture review.")
    if st.session_state.get("review_error"):
        st.error(st.session_state["review_error"])
    entry = active_review(st.session_state)
    if entry is None:
        with st.container(key="results_empty"):
            st.markdown('<div class="empty-state"><strong>No search yet</strong><p>Enter your architecture and review request, optionally upload policies, then select Review to find AWS documentation.</p></div>', unsafe_allow_html=True)
        return
    if entry.error:
        st.error(entry.error)
        return
    if not entry.sources:
        st.warning("No documentation found. Try a more specific review request.")
        return
    st.markdown(f'<div class="retrieval-summary"><strong>{len(entry.sources)} AWS documentation sources retrieved</strong><br>Official sources for your submitted request</div>', unsafe_allow_html=True)
    page = st.session_state["result_page"]
    pages = (len(entry.sources) + PAGE_SIZE - 1) // PAGE_SIZE
    start = page * PAGE_SIZE
    with st.container(key="source_cards"):
        for source in entry.sources[start:start + PAGE_SIZE]:
            render_source_card(source)
    if pages > 1:
        st.markdown(f'<style>.st-key-pagination .st-key-page_{page} button {{background:#4054b8!important;color:#fff!important;border:2px solid #9ba9ff!important;}}</style>', unsafe_allow_html=True)
        st.caption(f"Page {page + 1} of {pages}")
        with st.container(key="pagination", horizontal=True, horizontal_alignment="center", vertical_alignment="center"):
            st.button("‹", key="previous_page", help="Previous page", disabled=page == 0,
                      on_click=change_page, args=(page - 1,))
            for index in range(pages):
                st.button(str(index + 1), key=f"page_{index}", help=f"Go to page {index + 1}",
                          on_click=change_page, args=(index,))
            st.button("›", key="next_page", help="Next page", disabled=page == pages - 1,
                      on_click=change_page, args=(page + 1,))
    st.caption("Grounded architecture reviews will be available when Amazon Bedrock integration is completed.")


def main() -> None:
    st.set_page_config(page_title="AI Architecture Review", page_icon=Image.new("RGBA", (32, 32)), layout="wide", initial_sidebar_state="auto")
    st.markdown(PAGE_STYLES, unsafe_allow_html=True)
    from architecture_review.policy_upload import render_policy_upload, render_upload_control
    from architecture_review.review_session import initialise
    from architecture_review.web_components import render_history, render_saved_sources, render_sidebar, render_utilities

    initialise(st.session_state)
    render_sidebar()
    render_utilities()
    st.title("AI Architecture Review & Optimisation Assistant")
    st.caption("Explore AWS guidance and prepare company policies for future grounded architecture reviews.")
    view = st.session_state["workspace_view"]
    if view == "history":
        render_history()
        return
    if view == "saved":
        render_saved_sources()
        return
    from architecture_review.review_session import active_review
    if active_review(st.session_state) is not None:
        with st.expander("Edit request and policies", expanded=False):
            render_composer()
        with st.container(key="results_panel"):
            render_results()
    else:
        with st.container(key="review_workspace"):
            left, right = st.columns([1, 1.05], gap="large")
            with left:
                render_composer()
                if active_review(st.session_state) is not None:
                    st.rerun()
            with right:
                with st.container(border=True, key="results_panel"):
                    render_results()


def render_composer() -> None:
    from architecture_review.policy_upload import render_policy_upload, render_upload_control

    with st.container(key="composer"):
        request = st.text_area(
            "Architecture and review request", key="review_input", height=200, max_chars=12000,
            placeholder="Describe your AWS architecture, context and what you would like reviewed (security, compliance, cost or resilience). You can include multiple statements and questions.",
        )
        with st.container(horizontal=True, vertical_alignment="center", horizontal_alignment="distribute"):
            render_upload_control()
            submit = st.button("Review", key="submit_review", type="primary", icon=":material/play_arrow:",
                               help="Retrieve AWS documentation for your submitted text.")
        st.caption("Your message goes to AWS documentation search. Uploaded policies stay local and are not used in the search yet.")
    render_policy_upload()
    if submit:
        retrieve_results(request)


# Retained for existing callers/tests of the excerpt formatter.
def format_excerpt(text: str) -> str:
    from architecture_review.web_components import format_excerpt as format_text
    return format_text(text)


if __name__ == "__main__":
    main()

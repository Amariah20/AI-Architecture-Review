"""Scoped workspace styles; widget keys avoid generated CSS class names."""

PAGE_STYLES = """
<style>
[data-testid="stAppDeployButton"], [data-testid^="stStatusWidget"] {display:none!important;}
[data-testid="stPopoverButton"] > div > div[aria-hidden="true"] {display:none;}
.retrieval-summary {background:rgba(17,139,164,.10);border:1px solid rgba(17,139,164,.15);border-radius:9px;padding:12px 16px;font-size:.85rem;line-height:1.6;margin-bottom:6px;}
.result-label {display:block;border-radius:5px;background:rgba(128,145,165,.13);font-size:.75rem;font-weight:650;padding:4px 8px;white-space:normal;}
.result-label.takeaway {background:rgba(24,196,172,.20);}
.block-container {padding-top:2rem; padding-bottom:2rem; max-width:1400px;}
.st-key-utilities {position:fixed;top:.72rem;right:3.6rem;z-index:1000000;margin:0!important;}
.st-key-utilities [data-testid="stPopoverButton"] {border:0!important;background:transparent!important;box-shadow:none!important;min-height:36px;width:36px;padding:6px;}
[data-testid="stLayoutWrapper"]:has(> .st-key-utilities) {height:0;margin:0;}
[data-testid="stSidebarContent"] {display:flex;flex-direction:column;}
[data-testid="stSidebarUserContent"] {flex:1;min-height:0;display:flex;flex-direction:column;padding-top:.25rem;padding-bottom:1rem;}
[data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {flex:1;}
[data-testid="stSidebarUserContent"] > div {display:flex;flex-direction:column;flex:1;min-height:0;}
[data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_layout) {flex:1;min-height:0;}
.st-key-sidebar_layout {height:auto;flex:1;min-height:0;gap:.75rem;}
.st-key-sidebar_layout > [data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_footer) {margin-top:auto;}
.st-key-sidebar_nav {gap:.25rem;}
.st-key-sidebar_nav button {min-height:36px;padding:6px 12px;justify-content:flex-start!important;text-align:left;}
.st-key-sidebar_nav button > div, .st-key-sidebar_nav button > div > div {justify-content:flex-start!important;width:100%;}
.st-key-sidebar_nav button p {margin:0;font-size:.9rem;}
.st-key-sidebar_footer {padding-top:1rem;}
.st-key-sidebar_footer hr {margin:.5rem 0;}
.st-key-source_cards [class*="st-key-actions_"] {padding-top:16px;margin-top:6px;}
.policy-status {font-size:.8rem;line-height:1.5;color:inherit;opacity:1;margin-top:6px;padding-bottom:16px;}
.policy-status-normal {opacity:.75;}
.policy-status-error {color:#c62828;font-weight:600;}
.policy-status-warning {color:#a66b00;font-weight:600;}
@media(prefers-color-scheme:dark) {.policy-status-error {color:#ef7070;}.policy-status-warning {color:#d9aa35;}}
[data-testid="stSidebar"] {background-image:linear-gradient(rgba(95,180,225,.07),rgba(95,180,225,.07));}
.st-key-sidebar_nav button {color:inherit!important;background:transparent;border-color:transparent;}
.st-key-sidebar_nav button p, .st-key-sidebar_nav button span {color:inherit!important;}
.st-key-sidebar_nav button[kind="primary"] {background:rgba(50,175,205,.20)!important;color:inherit!important;border-color:transparent;}
.st-key-sidebar_nav button:hover {background:rgba(50,175,205,.12);}
h1 {font-size:1.8rem!important; letter-spacing:-.035em; line-height:1.25!important;}
h2 {font-size:1.18rem!important; letter-spacing:-.02em;}
h3 {font-size:1.02rem!important;}
button, input, textarea {border-radius:8px!important;}
button[kind="primary"] {background:#118ba4;color:#fff;border-color:#118ba4;}
textarea {line-height:1.65!important;}
.workspace-brand {border-left:4px solid #1099b2;padding:4px 0 4px 12px;font-weight:750;font-size:1rem;line-height:1.35;margin:0 0 8px;}
.st-key-utilities {margin-bottom:.5rem;}
.st-key-composer {border:1px solid rgba(128,145,165,.3);border-radius:12px;padding:16px;}
.st-key-results_empty {min-height:360px;display:flex;align-items:center;justify-content:center;}
.empty-state {text-align:center; padding:64px 20px;opacity:.8;}
.empty-state strong {display:block;font-size:1.05rem;margin:16px 0 8px;}
.empty-state p {max-width:320px;margin:auto;font-size:.92rem;line-height:1.6;}
.st-key-source_cards [data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;}
.st-key-source_cards p, .st-key-policy_list p {overflow-wrap:anywhere;}
.st-key-source_cards [data-testid="stVerticalBlock"] {gap:.55rem;}
.st-key-source_cards p {font-size:.85rem;line-height:1.45;margin-bottom:0;}
.st-key-source_cards [class*="st-key-source_"] {padding:14px 18px;}
.st-key-source_cards [class*="st-key-detail_"] {min-height:32px;}
.st-key-source_cards [class*="st-key-excerpt_result_"] [data-testid="stMarkdownContainer"],
.st-key-source_cards [class*="st-key-excerpt_saved_"] [data-testid="stMarkdownContainer"] {font-style:italic;}
.st-key-source_cards .source-title {font-size:1rem;}
.source-title {font-weight:700;font-size:1.04rem;line-height:1.4;color:#1674df;margin:0;overflow-wrap:anywhere;}
.st-key-source_cards [data-testid="stCaptionContainer"] p {font-size:.76rem;}
.st-key-source_cards [data-testid="stHorizontalBlock"] {align-items:start;}
.st-key-source_cards [data-testid="stMarkdownContainer"] p {margin-top:0;}
.policy-name {font-size:.9rem;font-weight:650;overflow-wrap:anywhere;margin:0;}
.document-type {display:inline-block;padding:2px 5px;border:1px solid currentColor;border-radius:4px;font-size:.65rem;font-weight:700;}
.status-ready {color:#087b5a;} .status-warning {color:#b26c00;}
.st-key-policy_list [data-testid="stCaptionContainer"] {font-size:.8rem;}
.st-key-pagination {border:1px solid rgba(128,145,165,.25);border-radius:999px;background:var(--secondary-background-color);padding:6px 12px;margin-top:12px;}
.st-key-pagination button {border:none;border-radius:50%!important;min-width:36px;width:36px;height:36px;min-height:36px;padding:0;background:transparent;color:var(--text-color,#777);}
.st-key-pagination button p {color:inherit!important;}
.st-key-pagination button:disabled {opacity:1;color:#888!important;background:transparent;}
.st-key-pagination button:focus-visible {outline:2px solid #6478e8;outline-offset:2px;}
.review-loading {position:fixed;inset:0;z-index:999999;display:flex;align-items:center;justify-content:center;background:rgba(128,128,128,.12);}
.review-loading-card {background:var(--background-color,white);color:var(--text-color,#222);border-radius:20px;padding:32px 42px;text-align:center;box-shadow:0 8px 40px rgba(0,0,0,.12);}
.review-loading-circle {width:58px;height:58px;margin:0 auto 20px;border:6px solid #ddd;border-top-color:#128da6;border-radius:50%;animation:review-spin .9s linear infinite;}
@keyframes review-spin {to {transform:rotate(360deg);}}
@media(prefers-reduced-motion:reduce) {.review-loading-circle {animation-duration:3s;}}
@media(max-width:1100px) {
 .st-key-review_workspace > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {flex-wrap:wrap;}
 .st-key-review_workspace > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width:100%!important;flex:1 1 100%!important;min-width:0!important;}
}
@media(max-width:600px) {
 .block-container {padding-left:1rem;padding-right:1rem;}
 h1 {font-size:1.4rem!important;}
 .st-key-composer {padding:10px;}
 .st-key-results_empty {min-height:220px;}
 .empty-state {padding:28px 10px;}
}
@media print {
 [data-testid="stSidebar"], header, .st-key-utilities, .st-key-pagination, .st-key-source_actions {display:none!important;}
 .st-key-review_workspace > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {display:block;}
 .st-key-review_workspace > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width:100%!important;}
 button {display:none!important;}
}
</style>
"""

LOADING_OVERLAY = """
<div class="review-loading" role="status" aria-live="polite">
 <div class="review-loading-card"><div class="review-loading-circle" aria-hidden="true"></div>
 <strong>Finding AWS documentation</strong><br>Please wait</div>
</div>
"""

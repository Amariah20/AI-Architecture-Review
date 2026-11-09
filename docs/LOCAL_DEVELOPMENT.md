# Local development

Run these commands in PowerShell from `C:\Users\rigod\AI-Architecture-Review`.
Python 3.14.10 and the existing `.venv` are used. Activation is optional because
the commands explicitly select the virtual environment's Python.

## Install declared dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

This installs the local package in editable mode and its declared dependencies.
The application has no AWS credential requirement for documentation retrieval.

## Start the local web interface

```powershell
Push-Location src
try {
    ..\.venv\Scripts\python.exe -m streamlit run architecture_review/web_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
}
finally {
    Pop-Location
}
```

Open <http://127.0.0.1:8501> in your browser. Enter a synthetic architecture
description and questions in **Architecture and review request**, then select **Review**. Up to three
results per page show titles, formatted excerpts and an **Open source** link.
The app automatically fetches up to nine results. Numbered page buttons and
chevrons below the results reuse session results without new AWS requests.
AWS may return fewer results than requested. A centered loading indicator appears while
searching. Press Ctrl+C in the terminal to stop the server.

Input is sent to the public AWS Knowledge MCP endpoint. Do not enter credentials,
private company information or policies in the architecture/request field.
Only this submitted text goes to AWS search. The separate policy uploader processes synthetic
documents locally and does not add them to searches. No model-generated review,
Bedrock calls or AWS resource provisioning are implemented. Search relevance
depends on the description and question. Results remain in the current browser
session for pagination; there is no durable search history or shared cache.
Use the native three-dot menu at the top right for Light/Dark/System and Print.
Browser printing may offer Save as PDF; generated PDF/Word export is not implemented.
Figures referenced in text can be viewed on the original source page.

## Existing terminal interface

```powershell
Push-Location src
try {
    ..\.venv\Scripts\python.exe -B -m architecture_review.mcp_probe
}
finally {
    Pop-Location
}
```

## Automated tests

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

UI tests use Streamlit AppTest with simulated retrieval responses. They do not
call AWS or prove current live service availability.

## Local policy document processing

Use **Upload policy document** beside the composer to add synthetic PDF, DOCX or
UTF-8 TXT documents, together or sequentially. Earlier uploads remain in compact
rows. Extraction/OCR runs once per upload. Each row shows filename, format, size,
status and a manual-review indicator when needed. Open **Processing details** for
safe warnings and page references. Extracted policy text is never displayed.
Remove a row to release its extracted content, or use **Clear all**. The same
filename and bytes are deduplicated; different bytes with the same filename are
retained as distinct documents, with a variant label. Session upload limits are
10 documents / 50 MiB total, in addition to the configured per-file limit.
Refreshing/disconnecting may lose session data; it is not durable storage.

Policy files are read from bytes in memory. No documents or extracted text are
written to disk, logged or sent to AWS. Results are stored in this session's
`policy_documents` as `PolicyUpload` records holding `ProcessedDocument` objects
with ordered `Passage` objects. Raw upload widgets reset after processing so the
application does not keep an additional raw-byte copy in its own session records.
These are extraction units, not RAG chunks. Each passage has text, a structural
location, optional PDF page number, status, warnings and `may_require_ocr`.

Defaults: 10 MiB upload, 200 PDF pages, 30 MiB expanded DOCX archive / decoded PDF
page content, 2,000 DOCX archive members, 1,000,000 extracted characters and
20,000 passages. Programmatic callers can supply `ProcessingLimits`. To change
the web upload limit (1–25 MiB), set this before launching Streamlit:

```powershell
$env:POLICY_MAX_UPLOAD_MB = "10"
```

These are application limits, not a hard CPU/memory sandbox. PDF decoding may
allocate memory before our decoded-content check; do not expose this local
prototype as a public upload service without isolated processing and stronger
resource controls.

Extracted policy text is never displayed, including in development mode. The
former preview environment flags are no longer used. Status, warnings, filenames
and page references remain visible; full text stays in session memory.

### Extraction limitations

- PDF text is extracted page by page. A page without usable text may be scanned,
  blank or unsupported. Its reference is retained and marked for possible OCR or
  manual review. Text presence does not prove all content on a page was captured.
- DOCX main-body paragraphs and tables (including nested tables) retain structural
  locations. Page numbers are not invented. Headers, footers, text boxes, tracked
  changes and images may be absent; a scope warning is shown.
- TXT uses UTF-8 (optional BOM); nonempty readable lines retain original line
  numbers. Invalid encoding/binary controls are rejected.
- Encrypted PDFs/Word files, legacy DOC, macros and corrupted or mismatched files
  are rejected with safe messages. No password handling, chunking, embeddings,
  vector storage or RAG integration is implemented. Optional PDF OCR is described below.
- Parser diagnostics are suppressed for privacy. Error messages never include
  the original parser error or extracted content.

Synthetic tests build PDF/DOCX documents in memory, including an image-only PDF,
and use simulated uploads for UI checks. Actual file-picker/browser interaction
are complemented by browser checks described in the implementation report.

## Workspace, history and bookmarks

- Desktop uses two columns; tablet/mobile stack composer and results. The native
  sidebar collapse/expand control remains available on narrow screens.
- A submitted message can contain multiple statements/questions. No LLM query
  rewriting is applied. The terminal entry point is unchanged.
- **Session history** retains submitted messages, source snapshots, generic
  retrieval errors and uploaded filenames at submission. It never snapshots
  extracted policy content. Open an entry to restore its message/results without
  another MCP call; current uploaded policies are not restored from history.
- **Save** on a documentation card bookmarks that source by URL. **Saved sources**
  shows bookmarks with original links; **Saved** removes one. No duplicates are
  created for the same URL across searches.
- **New review** clears the draft and current policy documents, while preserving
  this session's history and bookmarks. Closing/disconnecting may lose everything;
  nothing is written to files, a database or browser local storage by the app.
- Cards show real titles, source excerpts and URLs. Main takeaway / Why relevant
  contain explicit Bedrock-not-yet-implemented placeholders, not findings.
- The native three-dot menu provides Light/Dark/System switching and Print.
  There is no custom theme toggle or browser DOM adapter. Printing covers the
  displayed page; Save as PDF depends on the browser. No generated reports.
- The sidebar follows Streamlit's light/dark theme with a subtle blue tint;
  navigation inherits the theme text colour.
- The info icon explains current capabilities, local processing and temporary
  session retention. Development-only synthetic-example banners are removed.

The project configuration in `src/.streamlit/config.toml` uses viewer toolbar
mode to disable developer controls at startup. The native menu remains available;
the separate info icon uses a native Streamlit popover. Launch from `src/` as shown above so Streamlit reads it.
Activity-icon CSS is applied before document-processing imports. Restart the
server after configuration changes.

## Automatic local OCR

Tesseract is a separate Windows application, not a pip package. This workstation
was installed with the UB Mannheim Tesseract 5.4.0.20240606 package through winget,
including English (`eng`) and orientation (`osd`) data. On another Windows machine:

```powershell
winget install --id UB-Mannheim.TesseractOCR --exact --source winget
```

The application checks PATH and the standard Program Files locations. For a
custom installation, set `TESSERACT_CMD` to its absolute executable path before
launching. Verify the engine and English data, for example:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs
```

Python rendering uses the pinned `pypdfium2` dependency. No Poppler or pytesseract
is needed. The native engine reads installed language files, but document bytes,
rendered images and recognised text travel through memory pipes, not temporary
document files. No OCR content is sent to AWS or logged.

Upload a PDF. If embedded text extraction finds flagged pages, OCR runs
automatically once for that upload, without a separate button. Only
unattempted flagged pages are processed; existing readable passages are retained.
Successful pages are labelled `extraction_method="ocr"` and `ocr_attempted=True`,
with original page numbers. OCR output still needs manual verification, so the
document keeps a further-processing/review status. Failed or blank pages remain
flagged with safe warnings. To retry already attempted pages, re-upload the PDF.

Limits per upload: five flagged pages, up to 300 DPI, 12 million pixels per page,
30 seconds per rendering child, 30 seconds per Tesseract child and a 120-second
overall processing deadline. Pages beyond these limits remain flagged; split a large PDF into smaller
documents or review the remaining pages manually. Ordinary UI reruns do not
repeat OCR, including after an engine error. Each rendering operation runs in a separate process because
PDFium is not thread-safe. Overdue direct child processes are killed and waited
for by Python. These controls are not an OS memory sandbox and OCR accuracy is
not guaranteed, especially for rotated text, handwriting, tables or poor scans.

OCR tests include real in-memory synthetic PDF rendering and Tesseract
recognition when the engine is present. The real-recognition test is skipped
on machines without Tesseract; mocked OCR and privacy tests still run.

After searching, results use the full workspace width. The request and uploads
remain under **Edit request and policies**. Cards omit review context and hostname
metadata. **Full retrieved excerpt**, immediately before **Open source**, opens a
modal with the original retrieved text without making another AWS request.
The native toolbar is enabled by `ui.hideTopBar = false`; activity icons are hidden
by application CSS once the UI loads. The top bar must remain enabled for the
native theme and Print menu in this Streamlit build.

The unboxed info icon is aligned alongside the native menu. Sidebar navigation
is compact and the session notice sits at the bottom, scrolling normally when
content exceeds the viewport. Upload removal uses an icon only; errors are red
and manual-review notices are amber, with text labels retained for accessibility.
Result actions have extra space above them, and the second field is Relevance.
Streamlit may briefly show its native running indicator before application CSS
arrives on a cold load. Hiding it after render does not guarantee zero startup
flash; the native menu is retained rather than modifying installed framework files.

Sidebar sizing uses the native available-height flex layout, without forcing a
viewport minimum height. Its footer stays below navigation and moves down into
available space. Scrolling remains available when content genuinely exceeds
the viewport. Native collapse/expand controls are not restyled. Document status
rows include 16 pixels of bottom padding.

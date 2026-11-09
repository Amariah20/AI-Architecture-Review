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
description and a review question, then select **Find AWS guidance**. Up to three
results per page show titles, formatted excerpts and an **Open source** link.
The app automatically fetches up to nine results. Numbered page buttons and
chevrons below the results reuse session results without new AWS requests.
AWS may return fewer results than requested. A centered loading indicator appears while
searching. Press Ctrl+C in the terminal to stop the server.

Input is sent to the public AWS Knowledge MCP endpoint. Do not enter credentials,
private company information or policies in the architecture/question fields.
These fields go to AWS search. The separate policy uploader processes synthetic
documents locally and does not add them to searches. No model-generated review,
Bedrock calls or AWS resource provisioning are implemented. Search relevance
depends on the description and question. Results remain in the current browser
session for pagination; there is no durable search history or shared cache.
The three-dot menu retains theme settings and printing. Use your browser's
Print / Save as PDF for the currently displayed page; Word export is not implemented.
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

Upload one synthetic PDF, DOCX or UTF-8 TXT in **Company policy document**.
Extraction runs once per upload. The UI shows the filename, format, status and
warnings, including PDF page numbers needing review. It does not show extracted
policy text by default. Removing/replacing the upload clears its extracted state.
Refreshing/disconnecting may lose session data; it is not durable storage.

Policy files are read from bytes in memory. No documents or extracted text are
written to disk, logged or sent to AWS. Results are stored in this session's
`policy_document` as a `ProcessedDocument`, containing ordered `Passage` objects.
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

### Development preview only

The environment defaults to `production`, with previews disabled. For local
debugging with synthetic policies only, explicitly set both:

```powershell
$env:APP_ENV = "development"
$env:POLICY_DEV_PREVIEW = "true"
```

A labelled, collapsed expander then permits at most 500 extracted characters
(and never the entire document). A production configuration suppresses previews
even if `POLICY_DEV_PREVIEW` is true. Return to safe defaults with:

```powershell
$env:APP_ENV = "production"
$env:POLICY_DEV_PREVIEW = "false"
```

No `.env` file is required or created.

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
  are rejected with safe messages. No password handling, OCR, chunking, embeddings,
  vector storage or RAG integration is implemented.
- Parser diagnostics are suppressed for privacy. Error messages never include
  the original parser error or extracted content.

Synthetic tests build PDF/DOCX documents in memory, including an image-only PDF,
and use simulated uploads for UI checks. Actual file-picker/browser interaction
still needs a manual local check.

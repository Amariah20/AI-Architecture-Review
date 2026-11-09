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
private company information or policies. No model-generated review, uploads,
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

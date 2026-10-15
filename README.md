# Kaizen Cross-Check

[![CI](https://github.com/Rahulreddy-23/Kaizen/actions/workflows/ci.yml/badge.svg)](https://github.com/Rahulreddy-23/Kaizen/actions/workflows/ci.yml)

Compare JDE bills of materials with product labels, drawings, change orders and label revisions.
Every recommendation includes an explanation and source evidence; reviewers record the final decision.

**Deployment:** runs locally today. Docker and Render configuration are prepared; Render deployment is the next step. GitHub CI does not deploy the app.

## Capabilities

- Five cross-checks: BOM–Label, BOM–Drawing, Label–Drawing, PCO–BOM and Old–New label, plus missing-document coverage.
- SKU-grouped documents, searchable source/discrepancy lists, paginated review queues and source-page references.
- BD accounts, private runs, View/Edit sharing, independent copies, decisions and explicit approvals.
- Versioned terminology and independently verified closed-testing feedback. Uncertain component matches, assemblies, quantity bases and drawing applicability remain review-required.
- Per-SKU Excel downloads (**Summary** or **Complete details**), decision imports, annotated BOM PDFs, certificates, action items and run comparisons.

## Quick start

Requires **Python 3.12+** and **Node.js 20+**. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
npm --prefix ui ci
npm --prefix ui run build
.venv/bin/kaizen serve
```

<details>
<summary>Windows PowerShell</summary>

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
npm --prefix ui ci
npm --prefix ui run build
.\.venv\Scripts\kaizen.exe serve
```

</details>

Open **http://127.0.0.1:8765**. Register with an `@bd.com` address and sign in immediately; administrator approval is not required.

1. On **All runs**, choose **New cross-check** and upload a folder or individual files. Choose **Try a demo** for synthetic examples.
2. Open **Documents** to inspect extraction, then **Review queue** to check comparisons against source evidence.
3. Save decisions and approve reviewed results. On **Overview**, use **Download Excel** for a summary or complete details, with each SKU on its own worksheet. Both support decision imports. View-only users cannot change or export runs.

## Inputs and storage

| Document | Formats |
| --- | --- |
| BOM | JDE PDF, XLSX, XLSM, CSV |
| Label / previous label | PDF |
| Drawing | PDF |
| PCO | FM00835 PDF, XLSX, XLSM, CSV |

Keep each SKU's documents in its own subfolder when possible, with PCO files included in the upload.
Word files are unsupported. Scanned PDFs need offline OCR: install Tesseract with English data or the optional Python extra (`.venv/bin/pip install -e ".[ocr]"`).

The default workspace is `kaizen-workspace/`; change it with `--workspace <folder>` or `KAIZEN_WORKSPACE`.
Real BD documents, review databases, credentials and generated reports stay in ignored local folders.
`datasets/golden/` contains the versioned synthetic fixtures used by tests and the demo.

For batch processing without the website:

```bash
.venv/bin/kaizen run <document-folder> --out out/check
.venv/bin/kaizen --help
```

## Development and checks

For UI development, start the API, then run `npm --prefix ui run dev` in a second terminal.
Vite serves the UI at http://localhost:5173 and proxies API calls to port 8765.

```bash
.venv/bin/pytest tests/unit tests/integration tests/golden
.venv/bin/kaizen eval datasets/golden --fail-under 1.0 --out out/eval
npm --prefix ui test
npm --prefix ui run build
```

On Windows, use `.\.venv\Scripts\kaizen.exe` and `.\.venv\Scripts\pytest.exe` for the corresponding commands.
CI runs Python lint/tests on 3.12 and 3.13, the synthetic accuracy gate, UI tests and the production build.

Matching and OCR run locally by default. Optional external AI only adds labelled suggestions.
Synthetic accuracy does not establish real-data accuracy; drawing images, placement and handwritten changes still need human review. See [limitations](docs/known-limitations.md).

## Guides

- [Review walkthrough](docs/demo-script.md) · [Accounts, sharing and deployment](docs/hosted-collaboration.md)
- [Closed testing and learning](docs/closed-testing.md) · [Relationship imports](docs/relationship-import.md)
- [Architecture](docs/final-architecture.md) · [API](docs/api-contract.md) · [UI development](ui/README.md)
- [Test strategy](docs/test-strategy.md) · [Real-data validation](docs/real-data-validation.md) · [Security](docs/security-review.md)

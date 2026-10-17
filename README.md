# Kaizen Cross-Check

[![CI](https://github.com/Rahulreddy-23/Kaizen/actions/workflows/ci.yml/badge.svg)](https://github.com/Rahulreddy-23/Kaizen/actions/workflows/ci.yml)

Compare JDE bills of materials with product labels, drawings, change orders and label revisions.
Every recommendation includes an explanation and source evidence; reviewers record the final decision.

**Deployment:** the Singapore Render pilot is provisioned for invite-only testing; local preview remains available. See [launch checks and budget](docs/testing-launch.md). Releases require passing CI and hosted acceptance checks.

Read the [user tutorial](docs/user-guide.md) and [privacy/document-handling notice](docs/privacy.md). Both are also available in the website before sign-in.

## Capabilities

- Five cross-checks: BOM–Label, BOM–Drawing, Label–Drawing, PCO–BOM and Old–New label, plus missing-document coverage.
- SKU-grouped documents, searchable source/discrepancy lists, paginated review queues and source-page references.
- Invite-only BD accounts, private runs, rename/delete/restore, View/Edit sharing, independent copies, decisions and explicit approvals.
- Shared reviewer-approved terminology, with named approvals and optional account selections; independently verified closed-testing feedback. Uncertain component matches, assemblies, quantity bases and drawing applicability remain review-required.
- Per-SKU Excel downloads (**Summary** or **Complete details**), decision imports, annotated BOM PDFs, certificates, action items and run comparisons.

## Quick start

**Automatic setup/repair** (after cloning or pulling the latest checkout):

```powershell
# Windows PowerShell
.\scripts\setup-local.ps1
```

```bash
# macOS / Linux
bash scripts/setup-local.sh
```

The script checks versions, installs missing Python/Node runtimes locally where supported, installs the
app with offline OCR, builds the website and tests scanned label/drawing extraction. Add `--check-only`
to diagnose without installing. Send `out/setup-report.json` when reporting a setup problem; it contains
versions and synthetic test results, without customer documents or credentials. Then start with
`.venv/bin/kaizen serve` (Windows: `.\.venv\Scripts\kaizen.exe serve`).

<details>
<summary>Manual setup</summary>

Use **Python 3.12 or 3.13** (tested) and **Node.js 20+**. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/kaizen doctor
npm --prefix ui ci
npm --prefix ui run build
.venv/bin/kaizen serve
```

<details>
<summary>Windows PowerShell</summary>

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\kaizen.exe doctor
npm --prefix ui ci
npm --prefix ui run build
.\.venv\Scripts\kaizen.exe serve
```

</details>

</details>

Open **http://127.0.0.1:8765**. New workspaces need an initial administrator: set `KAIZEN_ADMIN_EMAIL`
and `KAIZEN_ADMIN_PASSWORD` privately before the first server start, then remove the bootstrap password
after setup. Existing approved accounts keep their access. No Supabase project is needed.

Administrators use **Manage users → Invite a reviewer**. Share the one-use code privately with the intended
BD recipient; it expires after 72 hours. The recipient chooses **Accept invitation**, enters that BD address
and code, and creates a password. A BD address alone cannot register.

1. On **All runs**, choose **New cross-check** and upload a folder or individual files. Choose **Try a demo** for synthetic examples.
2. Open **Documents** to inspect extraction, then **Review queue** to check comparisons against source evidence.
3. Save decisions and approve reviewed results. On **Overview**, use **Download Excel** for a summary or complete details, with each SKU on its own worksheet. Both support decision imports. View-only users cannot change or export runs.

In **Terminology**, filter the **Shared library** by **Approved by**, then add the entire list or select
individual entries. **My terminology** shows what your future uploads use. Approval adds the entry to its
author’s account; other users opt in. Edits require deliberate version updates; past runs retain their snapshots.

## Inputs and storage

| Document | Formats |
| --- | --- |
| BOM | JDE PDF, XLSX, XLSM, CSV |
| Label / previous label | PDF |
| Drawing | PDF |
| PCO | FM00835 PDF, XLSX, XLSM, CSV |

Keep each SKU's documents in its own subfolder when possible, with PCO files included in the upload.
Word files are unsupported. Offline OCR and its models are installed automatically, including for scanned
labels and drawings. Tesseract with English data is an optional additional engine; it is not required.
For an existing checkout, pull the changes, repeat the Python install command above, run `kaizen doctor`,
then restart the server and create a new run (saved runs retain their original extraction).
See [PDF/OCR setup](docs/pdf-ocr.md) if a dependency or scan cannot be read.

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
CI runs Python lint/tests on 3.12 and 3.13, the synthetic accuracy gate, UI tests, the production build
and an offline OCR smoke test inside the deployment image.

Matching and OCR run locally by default. Hosted/confidential mode blocks external AI and password providers.
Outside confidential mode, optional external AI only adds labelled suggestions.
Synthetic accuracy does not establish real-data accuracy; drawing images, placement and handwritten changes still need human review. See [limitations](docs/known-limitations.md).

## Guides

- [Review walkthrough](docs/demo-script.md) · [Accounts, sharing and deployment](docs/hosted-collaboration.md)
- [Closed testing and learning](docs/closed-testing.md) · [Relationship imports](docs/relationship-import.md)
- [Architecture](docs/final-architecture.md) · [API](docs/api-contract.md) · [UI development](ui/README.md)
- [Test strategy](docs/test-strategy.md) · [Real-data validation](docs/real-data-validation.md) · [Security](docs/security-review.md)

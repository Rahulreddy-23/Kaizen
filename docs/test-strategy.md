# Test strategy

Use synthetic fixtures for public regression tests and isolated workspaces for manual changes.
Private BD files, screenshots, review databases and detailed adjudications remain local and ignored.

## Commands

From an installed checkout ([setup](../README.md)):

```bash
KAIZEN_WORKSPACE="$PWD/out/test-workspace" .venv/bin/pytest tests/unit tests/integration tests/golden
KAIZEN_WORKSPACE="$PWD/out/eval-workspace" .venv/bin/kaizen eval datasets/golden --fail-under 1.0 --out out/eval
npm --prefix ui test
npm --prefix ui run build
```

For lint parity with CI, install `ruff` in the virtual environment and run `.venv/bin/ruff check src tests`.
Windows uses the corresponding `.venv\Scripts\` executables and PowerShell environment assignment.
The full Python suite can take several minutes; runtime depends on hardware and the installed OCR engine.
CI runs Python 3.12/3.13 lint, tests and the synthetic precision/recall gate, plus UI tests and build.
It does not deploy or validate a live Render service.

## Regression coverage

Test paths below are relative to `tests/` unless prefixed with `ui/`.

| Area | Representative tests | Assertions |
| --- | --- | --- |
| Models and normalization | `unit/test_models.py`, `test_normalize.py`, `test_hardening.py` | Valid evidence/quantities, preserved raw text, deterministic matching keys and fused-word/unit handling. |
| Extraction | `unit/test_bom_pdf.py`, `test_bom_table.py`, `test_label_pdf.py`, `test_drawing.py`, `test_pco.py`, `test_real_layouts.py` | JDE columns, wrapped/multi-column labels, rotated boxes, PCO tables, duplicates, malformed/encrypted inputs and warnings. |
| OCR | `unit/test_ocr_and_extraction_method.py`, `integration/test_offline_ocr.py`, `integration/test_pdf_ocr_layouts.py`, `unit/test_ocr_runtime.py` | Engine failure/fallback/confidence/geometry paths; mandatory portable OCR execution on native/raster/outlined labels and raster drawings, including partial text layers. |
| Matching and quantities | `unit/test_component_candidates.py`, `test_ladder.py`, `test_assignment.py`, `test_quantity_compare.py` | Unseen item codes/wording, reversed callout order, object/accessory distinctions, conflicting specifications, alternatives, ambiguity and pack/pair bases. |
| Check policies | `unit/test_bom_label_check.py`, `test_pco_bom_check.py`, `test_label_revision.py`, `test_check_sweep_regressions.py` | Applicable sources, PCO/revision changes, coverage, exemptions and uncertainty rather than false auto-clears. |
| Accounts and collaboration | `integration/test_auth_password.py`, `test_auth_supabase.py`, `test_collaboration.py`, `test_api_regressions.py` | Sign-in, revocation, grants, admin boundaries, same-origin changes, stale revisions, uploads and copies. |
| Learning and terminology | `unit/test_learning.py`, `test_worklist.py`, `test_terminology_source_import.py`, `integration/test_learning_api.py` | Immutable splits, independent verification, stale-label invalidation, learning eligibility and atomic imports. |
| Excel and PDF reporting | `unit/test_sku_excel.py`, `test_excel_review_export.py`, `test_excel_roundtrip.py`, `test_annotated_bom.py` | Per-SKU Summary/Complete layouts, safe sheet names/text, current review state, stable row IDs, imports/conflicts and source geometry. |
| Run comparison and follow-up | `unit/test_rundiff.py`, `test_action_items.py` | Relocated unchanged copies, actual content changes, disappeared comparisons and conservative verification. |
| Pipeline and evaluation | `unit/test_pipeline.py`, `test_dataset_build.py`, `golden/test_accuracy.py`, `integration/test_cli.py` | Saved metadata, reproducible synthetic documents, CLI workflows and declared accuracy floors. |
| UI controls/navigation | `ui/src/components/ChoiceList.test.tsx`, `ui/src/lib/neighbors.test.ts`, `ui/src/lib/uiLists.test.tsx`, `ui/src/pages/UIPass.test.tsx` | Selection survives search, unique document grouping, paging, validation, permissions and screen recovery. |
| Excel UI | `ui/src/components/ExcelExport.test.tsx`, `ui/src/pages/DashboardPage.test.tsx` | Download choices, focus/dismissal and overview integration. |

Short test filenames in a row use the same directory as its first Python test.
Parsers, checks, storage, exports and the API execute in regression tests; optional remote providers are
replaced with controlled responses. No real credentials or customer document pages belong in fixtures.

## Manual UI verification

Use synthetic data for saves, approvals, copies, imports and account-role checks. Exercise:

1. New cross-check: folder/individual uploads, selected-file paths, unsupported files and pending controls.
2. Lists: filtering, no matches, page boundaries, long descriptions and run/row changes without stale drafts.
3. Evidence: correct source pages, review save/reload, ground-truth search/chips and preserved selections.
4. Exports: Summary and Complete details per-SKU workbooks, import preview/conflicts, PDFs and ZIPs.
5. Permissions: viewer cannot mutate/export; owner sharing and admin-only controls remain distinct.
6. Desktop/narrow layouts, both themes, keyboard ownership, drawer/dialog focus and error recovery.

A viewport emulation check does not certify a physical mobile device or another browser engine.
Keep evidence under ignored `out/`, with the tested revision and source hashes where applicable.

## Real-data acceptance

An optional local audit compares BOM PDFs with independent spreadsheet exports:

```bash
.venv/bin/python scripts/audit_real_data.py trainingdataset --out out/real-bd
.venv/bin/pytest tests/real tests/unit/test_real_layouts.py
```

Run the private suite only when its source fixtures are present. Use clean PDFs and readable spreadsheet
counterparts; the marked-up attachment batch and Word documents are outside the agreed validation scope.
A passing extraction check or improved mapping coverage is not measured defect accuracy. Independently
verified pairing/discrepancy truth, drawing applicability and held-out SKU coverage remain necessary.
See [real-data validation](real-data-validation.md) and [closed testing](closed-testing.md).

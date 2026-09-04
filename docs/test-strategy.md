# Test strategy

Every layer has tests that were written before the code they exercise (test-first), and every bug found
during development got a regression test. The suite runs offline in about a minute: `.venv/bin/pytest`.

## Layers and what is asserted

| Layer | Tests | What is asserted |
|---|---|---|
| Canonical model | `tests/unit/test_models.py` | Validation (confidence 0–1, ordered bboxes, evidence required, non-empty explanations), enum coverage of the discrepancy taxonomy. |
| Normalisation | `test_normalize.py`, `test_hardening.py` | Table-driven: ™/®, `W/`, units, plurals, `.0`, `%`, dimensions, token order; determinism and idempotence. |
| Quantities | `test_quantity.py`, `test_quantity_compare.py` | `N Each -` parsing, `(3 per)`, `(1 pair)`, per-pouch idioms; unit-aware comparison and idiom reconciliation. |
| BOM categorisation | `test_bom_categorize.py` | Every category rule, zero and unreadable quantities, reasons are explanatory. |
| PDF primitives | `test_pdf_words.py` | Word boxes, line grouping (with sub-pixel jitter), column bands, gap splitting, annotation capture and exclusion. |
| Parsers | `test_bom_pdf.py`, `test_bom_table.py`, `test_label_pdf.py`, `test_pco.py`, `test_drawing.py`, `test_ocr_and_extraction_method.py` | Rendered fixtures designed to break naive extraction: multi-page BOMs, blank quantities, XLSX/CSV aliases, two/three-column labels, wrapped lines, decoy REFs, PCO XLSX and PDF forms, EN/ES callouts, conditional callouts, noise, image-only pages with and without an OCR engine (mocked). |
| Terminology | `test_terminology_store.py`, `test_terminology_repository.py`, `test_terminology_exchange.py` | Scope (global/family/SKU), item anchors (incl. the over-matching regression), versioning, history survives delete, historical run reconstruction, Excel/CSV round trips, `sync-defaults` never touching edited rows. |
| Matching | `test_fuzzy.py`, `test_ladder.py`, `test_assignment.py`, `test_semantic.py`, `test_providers.py` | Numeric guard, single-token guard, stopwords, level order, fuzzy never EXACT, ambiguity delta, contested candidates, semantic and AI layers can only yield POTENTIAL/weak outcomes. |
| Checks | `test_bom_label_check.py`, `test_pairing_engine.py`, `test_pco_bom_check.py`, `test_label_revision.py`, `test_adversarial.py` | Every classification and discrepancy type per check, REF/parent, duplicate BOM rows, unreadable label blocker, conditional/packaging exemptions, PCO ADD/DELETE/SUBSTITUTE/MODIFY with redlines, coverage blockers, expected vs unexpected label changes. |
| Review layer | `test_review_store.py`, `test_action_items.py`, `test_mining_and_business.py` | State machine, blind mode, disagreement, finalisation history, bulk accept, action items linked to rows, verify & close via comparison keys, mining evidence counts, business case honesty. |
| Reporting | `test_excel_report.py`, `test_excel_review_export.py`, `test_annotated_bom.py` | Sheet set and column order, conditional formatting and validations, metadata answers "where did this come from", decisions merged without touching engine columns, marks never over printed text, spreadsheet fallback. |
| Pipeline / CLI / API | `test_pipeline.py`, `test_detect_grouping.py`, `tests/integration/test_cli.py`, `test_cli_terminology.py`, `test_api.py` | Deterministic run ids, document-id uniqueness, grouping strategies, every CLI command, the full API contract including blind mode, save-as-relationship feeding the next run, mining, action items, exports, uploads and the demo loader. |
| Golden accuracy | `tests/golden/test_accuracy.py`, `tests/unit/test_dataset_build.py` | Floors on precision/recall/pairing/classification per check against a deterministic, byte-stable dataset whose ground truth is generated from the same scenario definitions. |
| Performance | `test_perf.py` (+ `kaizen perf`) | The harness builds N-SKU datasets and times ingest / matching / report. |

## Fixtures
Documents are rendered, not hand-drawn: `kaizen.datasets` produces JDE-style BOM prints (with FreeText redline
annotations), two-column labels, multi-sheet drawings and FM00835 PCO forms, all byte-stable. When a parser bug
is found, the failing fragment becomes a fixture (see `test_hardening.py`, `test_adversarial.py`).

## What is deliberately not mocked
Parsers, matching, checks, storage and the API run for real in tests. Only the OCR engine and the AI client are
faked (they are optional external components).

## Known gaps
Real JDE / MasterControl files are not in the suite yet (none available); `tests/fixtures/real/` is reserved for
them and the golden floors will be re-tuned when they arrive.

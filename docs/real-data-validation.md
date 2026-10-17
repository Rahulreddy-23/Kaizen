# Real-data validation

This public summary reflects the clean-document audit and subsequent matching verification completed
on 15 October 2026. Source files, detailed row assessments, screenshots, manifests and review databases
remain local under ignored source/workspace/output folders. No customer documents are included here.

## Scope

The latest clean upload used 26 files from the SKU and BOM cross-check folders: clean PDFs, duplicate
source copies, independent JDE spreadsheet exports and a protected relationship workbook. It produced
25 parsed documents across four SKU groups. The rights-managed workbook remained unreadable and warned
about; no terminology was imported from it.

The 30 unique PDF pages were inspected locally: 16 BOM pages, four label pages and ten drawing sheets.
The marked-up attachment folder, its ticks/strikeouts and Word files were excluded. Source documents
were preserved. This delivery did not supply a real PCO/revision pair or standalone case-label source.

## Evidence established

| Check | Local evidence and limit |
| --- | --- |
| BOM extraction | All 373 rows agreed with independently parsed spreadsheet exports, including quantities, units, sequence and other compared fields. This establishes extraction parity, not specification approval. |
| Labels | 140 label entries/quantities were manually checked; pack/pair markers remain explicit rather than guessed from equal numbers. |
| Drawings | Named callouts across all ten sheets were inspected. A later complete-output audit caught incorrect component/accessory pairings and false presence warnings missed by the earlier label-focused checklist. |
| Source retention | Source/upload hashes agreed; extraction text, quantities, categories and page references were retained through the matching correction. |
| Correction replay | All 58 definite pairing/presence-warning errors identified in that audit were resolved as candidates or appropriate exemptions. Six scoped-identity and six ambiguity checks also passed: 70 targeted acceptance checks in total. |

These counts describe one reviewed delivery and repeated comparison rows, not unique physical defects
or universal recall. Earlier September/October comparison totals are historical and are superseded by
this follow-up; do not use them as current product accuracy figures.

## General changes now in the app

- Recover terse/noun-first component wording with typed candidate guards, without SKU/item-specific mappings.
- Match the primary object before accessories; separate catheters from drapes, gloves from containers,
  and needles from holders. Preserve dimensional, gauge, volume, lumen and other explicit conflicts.
- Keep inferred assembly members and allocations review-required. Do not save assembly membership,
  overlabel configuration or ambiguous alternatives as equivalent terminology.
- Distinguish printed quantity equality from an unverified pack/pair basis and base artwork from final overlays.
- Withhold component findings for explicitly conflicting drawing references and preserve applicability questions.
- Reuse approved identities only within their scope/document types/item anchors; shorter wording stays a candidate.
- Display MISSING as Unmapped and uncertain rows as requiring review rather than asserting physical absence.

Thresholds were not relaxed. The private verification retained source hashes and compared the website
upload with a replay. Regression cases use changed wording/codes, reversed order, conflicting attributes,
explicit alternatives and mixed clinical/packaging contexts to protect behavior beyond this delivery.

## What remains unproven

The verified follow-up still had 385 comparisons awaiting review. No physical product defect was
conclusively established by that verification. Component identities/specifications, assembly allocations,
pack contents, final overlays, applicable work orders and a component-level IFU requirement need approved
source evidence where not supplied. OCR confidence warnings are not source-document defects.

Real-data precision, recall and false-clear rates require independently verified pairing/discrepancy
truth and representative held-out SKU coverage. Golden accuracy and the targeted audit are not substitutes.
Real PCOs, revision pairs and other layouts still need validation. The invite-only Render pilot is provisioned; see [launch checks](testing-launch.md).

## OCR setup follow-up — 17 October 2026

Local installs now include the offline OCR engine and bundled models. The same RapidOCR release is the
default on desktop and hosted installations, with Tesseract as backup. The previous Tesseract-first
selection returned nonempty but incomplete label text, preventing fallback. This is an extraction/setup
issue, not evidence of defects in the source documents. Native BOM parsing and matching thresholds are unchanged.

Use [automatic setup and diagnostics](pdf-ocr.md) after updating the checkout. Saved runs retain their
original extraction; restart the server and upload a new run to use parser changes. The clean-label
quantity and independent BOM-export checks are retained as local acceptance checks; they do not certify
all scanned text or establish general defect accuracy.

## Reproduce without publishing sources

```bash
.venv/bin/pip install -e ".[dev,ocr]"
.venv/bin/python scripts/audit_real_data.py trainingdataset --out out/real-bd
.venv/bin/pytest tests/real tests/unit/test_real_layouts.py tests/unit/test_extraction_robustness.py
.venv/bin/kaizen eval datasets/golden --fail-under 1.0 --out out/eval
```

The private test suite requires local sources. The audit writes `validation.md`, `validation.json`,
`run.json` and `report.xlsx` under ignored `out/`. For other local folders, substitute the input path.
Use [closed testing](closed-testing.md) to curate independent truth and
[relationship imports](relationship-import.md) for permitted readable terminology exports.

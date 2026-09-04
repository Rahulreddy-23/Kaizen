# Demo script (10–12 minutes)

Preparation (once): `python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]"`, build the UI
(`cd ui && npm install && npm run build`), then `rm -rf kaizen-workspace` for a clean start.
Start: `.venv/bin/kaizen serve` → open http://127.0.0.1:8765. Everything is local and deterministic.

| # | Beat | Where | What to say / show |
|---|---|---|---|
| 1 | The manual process | Slide 7 of the brief | An hour per SKU per reviewer, coloured pens, a separate tracker; the independent reviewer is only free half a day. |
| 2 | Drop the documents | Home → "Load demo dataset" (or drop the `datasets/golden` folder) | 10 SKU sets: BOM (PDF/XLSX/CSV), labels incl. old revisions, drawings, two PCOs. |
| 3 | Grouping | Dashboard → groups | Sets formed per folder / product family; documents by type; unrecognised files listed. |
| 4 | Missing BOM | Dashboard → coverage | PCO34590 lists affected code 1495108NS and there is no BOM for it: a BLOCKER before any comparison. |
| 5 | Run summary | Dashboard | ~1,100 comparisons across five checks; the big picture: AUTO-CLEARED vs NEEDS HUMAN REVIEW. |
| 6 | Measured accuracy | CLI `kaizen demo` output or the Accuracy sheet | Precision/recall per check against declared ground truth (24 seeded discrepancies). |
| 7 | A contextual match | Review queue → SKU 1295108NS, POTENTIAL, "CHLORAPREP" | BOM says `CHLORAPREP APPLICATOR 3ML`, label says `ChloraPrep™ Solution One-Step Applicator, 3 mL`. |
| 8 | Evidence both sides | Evidence view | BOM page 1 row highlighted on the left, label page column highlighted on the right; raw text and locators. |
| 9 | Why | Same view | Explanation: token similarity 1.00, threshold 0.85, no approved relationship → POTENTIAL, reviewer decides. |
| 10 | Reviewer accepts | Decision panel | ACCEPT as reviewer 1 with a comment. |
| 11 | Save as relationship | Same panel | Canonical = label wording, alias = BOM wording, anchored to item 4440003, provenance "learned". |
| 12 | Next SKU | Run `sku-002` again (Home → run local folder) | The same pair is now EQUIVALENT via the new relationship id: the next SKU already knows the terminology. |
| 13 | Terminology manager | #/terminology | Explicit, versioned rules with provenance, usage counts and history; `sync-defaults`, import/export. |
| 14 | A real quantity mismatch | Queue → 1295108FNS, MISMATCH | Gauze 10 on the BOM vs 8 on the label; END CAP 2 vs 1. |
| 15 | PCO change not applied | Queue → PCO_BOM, 1395108QNS | Scissors still on the BOM although the PCO deletes them; evidence is the BOM row. |
| 16 | A missing item | Queue → MISSING | Absorbent drape missing from the label (1395108QNS); label item without BOM line (1175108NS). |
| 17 | Blind independent review | Reviewer identity → slot 2, blind ON | Reviewer 2 sees evidence and the system recommendation, not reviewer 1's decision. |
| 18 | Second review | Decide CONFIRM_DISCREPANCY | State becomes DISAGREEMENT when the two differ. |
| 19 | Disagreement | Evidence view | Both decisions side by side; finalize with a note from the cross-check meeting. |
| 20 | Export Excel | Dashboard → Export | Sheets per check, Action Items, Coverage, Manual Checklist, Relationships Used with versions. |
| 21 | Hashes and snapshot | Run_Metadata / Relationships_Used sheets | SHA-256 of inputs, thresholds, terminology snapshot hash; historical runs reconstruct relationship versions. |
| 22 | Annotated BOM | Dashboard → Documents → BOM → annotated PDF | Coloured marks in the margin like their pens; spreadsheet BOMs get a review page. |
| 23 | Action item | Evidence view → Create action item | Linked to the row; owner, status. |
| 24 | Corrected rerun | Fix the BOM file (or use the corrected copy) → run → Verify & close | The item resolves against the new run by comparison key, not by file name. |
| 25 | Measured effort | #/runs/:id/business | Two numbers, both from this run: the **measured** reduction with default per-row assumptions (on the golden set ~27%, below the 50% target because the engine refuses to auto-clear ~190 strong fuzzy pairings), and the **projection** after those pairings are confirmed as relationships (~73%, ~29 rows left to validate). Say plainly which is which; the assumptions are listed beside them. |

Fallback if the UI is unavailable: `kaizen demo` (run + eval + workbook), `kaizen terminology ...`,
`kaizen runs relationships <run>`, `kaizen report`, and the workbook in Excel.

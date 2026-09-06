# Demo script (10–12 minutes)

Preparation (once): `python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]"`, build the UI
(`cd ui && npm install && npm run build`), then `rm -rf kaizen-workspace` for a clean start, and
`.venv/bin/kaizen dataset corrected 1295108FNS --out out/corrected` for beat 24.
Start: `.venv/bin/kaizen serve` → open http://127.0.0.1:8765. Everything is local and deterministic.

| # | Beat | Where | What to say / show |
|---|---|---|---|
| 0 | Sign in | Name + reviewer slot | Identity is server-side: every decision is recorded against this name, and slot 2 is blind whether or not the reviewer wants to be. The moon/sun button (top right, also in the top bar once signed in) switches between the light and dark theme; the choice is remembered, and until one is made the tool follows the operating system. Pick the theme that suits the room before you start. |
| 1 | The manual process | Slide 7 of the brief | An hour per SKU per reviewer, coloured pens, a separate tracker; the independent reviewer is only free half a day. |
| 2 | Drop the documents | Runs → "Load demo dataset" (or drop the `datasets/golden` folder) | 10 SKU sets: BOM (PDF/XLSX/CSV), labels incl. old revisions, drawings, two PCOs. |
| 3 | Grouping | Dashboard → groups | Sets formed per folder / product family; documents by type; unrecognised files listed. |
| 4 | Missing BOM | Dashboard → coverage | PCO34590 lists affected code 1495108NS and there is no BOM for it: a BLOCKER before any comparison. |
| 5 | Run summary | Dashboard | ~1,100 comparisons across five checks; the big picture: AUTO-CLEARED vs NEEDS HUMAN REVIEW. |
| 6 | Measured accuracy | CLI `kaizen demo` output or the Accuracy sheet | Precision/recall per check against declared ground truth (24 seeded discrepancies). |
| 7 | A contextual match | Review queue → SKU 1295108NS, POTENTIAL, "CHLORAPREP" | BOM says `CHLORAPREP APPLICATOR 3ML`, label says `ChloraPrep™ Solution One-Step Applicator, 3 mL`. |
| 8 | Evidence both sides | Evidence view | BOM page 2 row highlighted on the left (the kit BOM runs to three pages), label page 1 column highlighted on the right; raw text and locators. |
| 9 | Why | Same view | Explanation: token similarity 1.00, threshold 0.85, no approved relationship → POTENTIAL, reviewer decides. |
| 10 | Reviewer accepts | Reviewer decision card → Accept (or press `a`), comment, Record decision (or Enter) | Recorded as reviewer 1 with a comment; the toast confirms the row state. |
| 11 | Save as relationship | Terminology card → Save as relationship | Canonical = label wording, alias = BOM wording, anchored to item 4440003, provenance "learned". |
| 12 | Next SKU | Run `sku-002` again (Runs → Run a local path) | The same pair is now EQUIVALENT via the new relationship id: the next SKU already knows the terminology. |
| 13 | Terminology manager | #/terminology | Explicit, versioned rules with provenance, usage counts and history; `sync-defaults`, import/export. |
| 14 | A real quantity mismatch | Queue → 1295108FNS, MISMATCH | Gauze 10 on the BOM vs 8 on the label; END CAP 2 vs 1. |
| 15 | PCO change not applied | Queue → PCO_BOM, 1395108QNS | Scissors still on the BOM although the PCO deletes them; evidence is the BOM row. |
| 16 | A missing item | Queue → MISSING | Absorbent drape missing from the label (1395108QNS); label item without BOM line (1175108NS). |
| 17 | Blind independent review | Sign out, sign in as reviewer 2 | The BLIND chip appears. Reviewer 2 sees the evidence and the engine recommendation, never reviewer 1's decision, and the export and audit log are refused with a 403. Adding `&blind=false` to the URL changes nothing: the server decides. |
| 17a | Keyboard review | Press ? in the queue | j/k move, Enter opens, a/c/o/n choose, Enter submits: a 200-row queue without the mouse. |
| 18 | Second review | Decide CONFIRM_DISCREPANCY | State becomes DISAGREEMENT when the two differ. |
| 19 | Disagreement | Evidence view | Both decisions side by side; finalize with a note from the cross-check meeting. |
| 19a | Back to reviewer 1 | Sign out, sign in as reviewer 1 again | A blind session is refused the Excel export, the certificate and the audit log (403), because all three reveal reviewer 1's decisions. Everything from here on is done as reviewer 1. |
| 19b | Certificate | Dashboard → Certificate | One page per SKU: run id, every file hash, counts, both reviewers by name, open action items. The stamp they use today, made verifiable. |
| 20 | Export Excel | Dashboard → Export workbook | Sheets per check, Action Items, Coverage, Manual Checklist, Relationships Used with versions. |
| 21 | Hashes and snapshot | Run_Metadata / Relationships_Used sheets | SHA-256 of inputs, thresholds, terminology snapshot hash; historical runs reconstruct relationship versions. |
| 22 | Annotated BOM | Dashboard → Documents → BOM → annotated PDF | Coloured marks in the margin like their pens; spreadsheet BOMs get a review page. |
| 23 | Action item | Evidence view → Create action item | Linked to the row; owner, status. |
| 24 | Corrected rerun | `kaizen dataset corrected 1295108FNS --out out/corrected` beforehand → Runs → "Run a local path" → Dashboard → Verify and close | The corrected set is the same SKU with the seeded discrepancies removed. The item resolves against the new run by comparison key, not by file name. |
| 24a | Compare runs | Compare runs → choose the earlier run | Resolved, new and still-open discrepancies side by side; a comparison that vanished is "gone", not "fixed". |
| 24b | Excel round-trip (optional) | Review queue → Import from Excel | Fill the decision column offline, preview (dry run), apply. Only your own columns are read; a decision changed in the tool after the export is a conflict, never overwritten silently. |
| 25 | Measured effort | #/runs/:id/business | Two numbers, both from this run: the **measured** reduction with default per-row assumptions (on the golden set ~27%, below the 50% target because the engine refuses to auto-clear ~190 strong fuzzy pairings), and the **projection** after those pairings are confirmed as relationships (~73%, ~29 rows left to validate). Say plainly which is which; the assumptions are listed beside them. After ten timed decisions the per-row effort switches from the brief's assumption to the measured median and the page says so. Decide rows at a real reading pace during the demo: decisions under five seconds are not counted, and the median is what the audience will see. |
| 25a | Terminology worklist | Worklist and mining → Terminology worklist | The projection as a to-do list: "approving the top 5 pairings clears N rows (X%)". Approve one, re-run the next SKU, watch it clear. |

Fallback if the UI is unavailable: `kaizen demo` (run + eval + workbook), `kaizen terminology ...`,
`kaizen runs relationships <run>`, `kaizen report`, and the workbook in Excel.

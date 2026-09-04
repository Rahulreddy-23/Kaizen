# Kaizen Cross-Check — Problem Understanding & Winning Proposal

Source brief: `docs/reference/hackathon-problem-statement.pdf` (Innovation Week 2026, TCI Hackathon, BD / AAD,
"BOM Cross-Check Automation"). Status: **proposal for team alignment — nothing built yet.**

---

## 1. The problem in one paragraph

When Sustenance Engineering runs a change-control project (deck example: CC-2015-863, PVC → TPU at Reynosa,
129 SKUs), every impacted SKU's **BOM** (JDE), **unit/case labels**, **packaging drawing** and **PCO**
(MasterControl) must be cross-checked against each other before implementation. Today a BOM facilitator
(R&D/Quality) and an independent reviewer do it by eye: annotate PDFs, tick coloured check marks
("compared with PCO / Label / PKG drawing"), stamp "checked by + date", and keep a separate tracker for
traceability. ~60 min per SKU per reviewer (129 SKUs → 258 h → 16 person-days); the independent reviewer is
only free ~4 h/day; errors cause rework. The ask: extract, compare **contextually** (synonyms, not exact
words), classify matches/discrepancies, keep the **reviewer as final decision-maker**, and produce a
**traceable Excel report**. Target: 50% effort reduction, ~100 reviewer hours/project, ~$75k/year.

## 2. Context that shapes the design

| Fact from the brief | Design consequence |
|---|---|
| Regulated medical-device QA process (independent reviewer, BCMM memo, filing) | Every classification must be **explainable and reproducible**; tool recommends, humans decide; audit trail beats cleverness. |
| JDE / MasterControl changes are out of scope | Integration = works on the exact files reviewers already download. File in → Excel out. |
| Existing approval workflow must not change | Output artefacts mirror today's (tracker Excel, marked-up BOM) so adoption is zero-friction. |
| Independent reviewer is scarce (4 h/day) | Make the *second* review fast: pre-classified, filtered to what needs eyes, evidence side-by-side, independence preserved. |
| Large SKU families sharing components | Batch processing + relationships **keyed by item number** compound across SKUs. |
| Build 7 Sep – 5 Oct, 3 checkpoints, review 6–8 Oct, winner 13 Oct, socialising 13–31 Oct | Vertical slice first, then breadth; use checkpoints to get real documents and terminology from problem owners. |

## 3. The five cross-checks (what is actually compared)

From slides 5, 6, 16 and the worked examples on slides 7–9.

| # | Check | Side A | Side B | Must agree | Typical discrepancies |
|---|---|---|---|---|---|
| 1 | **BOM ↔ Label** | BOM component lines (item #, description, qty per, oper seq, parent item) | Label "Full Kit – Contents" lines (`N Each – Description`), REF | Each physical BOM component ↔ one label line (via terminology); qty per = label qty; BOM parent ↔ label REF (SKU family: `1295108NS` ↔ `REF 1295108`) | Qty mismatch; on BOM not on label; label line without BOM item; REF/parent mismatch |
| 2 | **BOM ↔ Packaging drawing** | BOM component lines | Drawing callouts (EN/ES pairs), drawing #, rev | Every physical component has a callout (presence only — drawing note: "for placement only, refer to work order for quantity"); drawing # matches BOM/label reference | Component missing from drawing; callout with no BOM item; wrong drawing #/rev |
| 3 | **Label ↔ Packaging drawing** | Label content lines | Drawing callouts | Same items on both | Item on one, not the other |
| 4 | **PCO ↔ BOM** | PCO form FM00835: affected codes, item # actual/proposed, description, qty, oper seq, ADD/DELETE/SUBSTITUTE | Redlined BOM | Every proposed change reflected (deleted item gone/struck; added item present with qty + oper seq); every affected code has a BOM in the batch | Change not applied; wrong qty/seq; BOM missing for an affected code |
| 5 | **Old ↔ New label** (unit and case; same engine for old ↔ new BOM) | Previous revision | New/unreleased revision | Only approved redline changes differ | Unexpected add/remove/change; expected change absent |

Slide 16 also lists "confirm dot sticker location per approved drawing" — visual; handled as a **manual checklist
item** carried in the report, not automated.

## 4. Document anatomy & quirks (from the real examples in the deck)

**JDE BOM print (report R30460)** — PDF, probably also Excel export. Header: Parent Item, Parent Description,
Branch/Plant, Batch Qty/UOM, Type, Bill Revision Level. Rows: Level, Component Item, Component Description,
Branch/Plant, Quantity Per, Ext Qty, UM, T, Effective From/Thru, Oper Seq No, flags.
- Many rows are **non-physical**: labels/packaging (`EN LOD, CASE LABEL`, `CASE LABEL, BLANK`, `LABEL, PRIMING
  VOLUME`), process items (`PRODUCING LABELS ON THE…`, `PACKAGING QUALITY`, `FIRST/LAST LABEL RECORD`), qty 0.
  These never appear on a label — categorise them, never report as "missing".
- Fractional quantities (`0.4000` case label allocation) vs `1.0000` for parts; Effective Thru dates
  (expired lines are inactive).
- **Redlines**: old → new in red (`PK0726442 → PK0722294`, `2000 → 0.4000`), as PDF annotations, overlaid
  text, or hand-drawn on scans.
- Terse ERP descriptions: `TAPE ANCHOR PER-Q-CATH`, `ABSORBENT TOWEL`, `EN LOD, UNIT LABEL`.

**Product label** — REF, product name, "Full Kit – Contents" in two columns: `1 Each - Towel, Absorbent`,
`10 Each - Gauze, 10 cm x 10 cm (4 in. x 4 in.)`, `2 Each - Tape Strips (3 per)`, `1 Each - Gloves (1 pair)`;
LOT/expiry, barcodes, peel-off sub-labels repeating REF. Multi-column layout garbles naive text extraction;
wrapped lines; ™/®; embedded sizes; parenthetical sub-quantities.

**Packaging drawing** — title block (`DWG3173108`, rev 11, title, plant), EN + ES callouts, conditional
callouts `(IF APPLICABLE PER BOM)`, cavity labels (not items), alternate views. Vector PDF usually; raster → OCR.

**PCO (form FM00835)** — Excel/PDF; New/Change/Substitute flags; Branch; Affected Codes (family with suffixes
`1175108NS`, `1295108FNS`, `1395108QNS`…); rows: Item Number Actual / Proposed (`DELETE` keyword),
Description, Qty actual/proposed, Oper Seq actual/proposed, scrap %.

## 5. Requirements → scoring

| Priority | Requirement (slide 10) | Criterion (weight) |
|---|---|---|
| Must | Extract & compare across BOM, label, drawing, PCO, multiple formats | 1 Extraction & comparison accuracy (25) |
| Must | Equivalent terminology via predefined relationships (`Tape Anchor = Surgical Tape = Tape Measure`) | 2 Contextual matching (20) |
| Must | Classify exact / equivalent / potential / mismatch / missing | 3 Discrepancy detection & reviewer support (20) |
| Must | Users add / modify / remove relationships | 2, 5 Usability (10) |
| Must | Traceable Excel: values, classification, relationship applied, discrepancies, needs-validation | 4 Traceability & Excel (15) |
| Must | Contextual not word-to-word; reviewer keeps final decision | 2, 3 |
| Nice | PDF, Excel, scanned & image files | 1, 6 Feasibility/scalability (5) |
| Nice | Batch processing of many SKUs | 5, 6 |
| Nice | Flag uncertain comparisons | 3 |
| Nice | Reduce effort & cycle time | 5 |
| Optional | Dashboard/UI for results & relationships | 5, 7 Innovation & demo (5) |

Mandatory to demo: contextual matching, editable relationships, discrepancy identification, reviewer
validation, Excel output.

## 6. How we win (thinking beyond the software)

**Who judges.** Problem owners are process/Quality people (they wrote "BOM facilitator", "BCMM", "independent
reviewer"). Their questions: *Does it catch what I catch by hand? Can I trust and audit it? Does it produce
the document I file? Will IT let me run it? Does it free my independent reviewer?*

**What competitors will likely build.** (a) "Upload PDFs to Copilot/ChatGPT and ask it to compare" — fast
demo, non-deterministic, no traceability, privacy questions, weak at 100 SKUs. (b) A fuzzy-match script with a
Streamlit table — decent, but no learning, no evidence, no process fit.

**Our levers, mapped to the weights.**

1. **Measured accuracy (25%).** Ship a golden dataset with *seeded* discrepancies and ground truth; the demo
   shows precision/recall per check ("47/47 seeded discrepancies caught, 2 false flags"). Turns "seems
   accurate" into a number.
2. **Explainable contextual matching (20%).** Every row states *why*: `Equivalent via REL-012 (Tape Anchor =
   Surgical Tape = Tape Measure)`. Relationships are scoped, item-number-anchored, versioned, and **learned
   from reviewer decisions** — SKU #2 is visibly faster than SKU #1 in the demo.
3. **Reviewer-centric discrepancy handling (20%).** Typed discrepancies with severity, a "needs validation"
   queue, evidence highlighted in the source page, two-reviewer sign-off with **blind mode** for the
   independent reviewer (preserves independence — a Quality principle judges will notice).
4. **Audit-grade Excel (15%).** File hashes, tool version, thresholds, relationship snapshot, stable row IDs,
   hyperlinks to source pages, reviewer columns that round-trip (edit in Excel, re-import).
5. **Fits the existing process (10%).** Zero source-system change; input = files they already download; output =
   the tracker they already keep + a marked-up BOM PDF with their coloured check marks. Plus it feeds the
   downstream steps they didn't ask about: **Findings & Action Items** list and a **BCMM memo draft**.
6. **Feasible & scalable (5%).** Offline by default, pip-installable, no admin rights (pure-Python OCR),
   100 SKUs in minutes, pluggable document types/checks, provider-agnostic optional LLM.
7. **Demo (5%).** A story, not a feature tour (section 12).

**Use the checkpoints.** Checkpoint 1: get 3–5 real (redacted) document sets and their synonym list from the
problem owners. Checkpoint 2: have them review classifications on their own documents. Checkpoint 3: dry-run
the demo with them. Solutions validated on the owners' own data win.

**Socialising phase (13–31 Oct).** One-command install, a 5-minute video, a one-page SOP-style guide, and a
roadmap slide (SharePoint watch-folder, Azure deployment, more document types) — shows the prototype has a
path to production.

## 7. Proposed solution

### 7.1 Principles
1. **Deterministic core, AI assist.** Normalisation + relationship dictionary + fuzzy/semantic matching
   produce every classification with a reason. An optional, pluggable LLM only (a) extracts structure from
   messy/scanned documents and (b) suggests adjudications for *potential* matches — never auto-accepts.
2. **Reviewer decides.** Every row carries decision fields for two reviewers; tool pre-fills recommendations
   and evidence.
3. **Traceable by construction.** Extracted value → file + page + bounding box; run → hashes, version,
   thresholds, relationship-dictionary version.
4. **Zero-change integration.** Files in, Excel out, artefacts mirror today's.
5. **Learns from reviews.** Confirmed potentials become relationships (optionally item-number anchored).
6. **Supports the whole 8-step process**, not only the comparison box: findings, action items, verify & close
   (re-run shows resolved items), BCMM draft.

### 7.2 Architecture

```
files (PDF / XLSX / images)
   │
   ▼
ingest ── doc-type detection, parsers (BOM, label, drawing, PCO), OCR fallback,
   │      redline/annotation extraction, SKU grouping
   ▼
canonical DocumentItems  {doc, page, bbox, item_number?, description, qty, uom, attrs, category, confidence}
   │
   ▼
matching engine ◄── terminology store (relationships: canonical, aliases, scope, item anchors, provenance, version)
   │   normalise → exact → relationship → fuzzy → semantic → (optional LLM) → assign → classify → explain
   ▼
checks (5 pluggable definitions) → CheckResults (rows with classification, score, reason, discrepancy type)
   │
   ▼
review store (SQLite) ◄── web UI / CLI: decisions, comments, two-reviewer sign-off, "save as relationship"
   │
   ▼
report: Excel workbook · annotated BOM PDF · action-items sheet · BCMM draft (docx)
```

Modules (each independently testable): `ingest/`, `terminology/`, `matching/`, `checks/`, `review/`,
`report/`, `api/`, `ui/`, `cli/`, `datasets/` (synthetic generator + golden ground truth), `eval/`
(accuracy harness).

### 7.3 Match ladder

| Level | Technique | Result |
|---|---|---|
| 0 | Normalise: case, punctuation, `W/`→`WITH`, ™/®, unit spelling (`5 mL`/`5ML`), singular/plural, drop Spanish half of callouts, `(IF APPLICABLE PER BOM)` → optional flag, token sort (`TOWEL, ABSORBENT` = `ABSORBENT TOWEL`) | comparable strings |
| 1 | Exact after normalisation | **Exact** |
| 2 | Relationship hit (term or item-number anchored, scope-aware) | **Equivalent** (+ relationship ID) |
| 3 | Token fuzzy similarity (rapidfuzz token-set) ≥ threshold | **Potential** (score) |
| 4 | Semantic similarity, small local embedding model (offline) | **Potential** (score) |
| 5 | Optional LLM adjudication with rationale | **Potential** + AI suggestion, flagged |
| — | Pair matched but qty/attribute differs | **Mismatch** (field, both values) |
| — | No candidate above floor | **Missing** (in which document) |

One-to-one assignment with conflict flags (one BOM item ↔ two label lines → flagged). Quantity comparison is
unit-aware and treats label idioms (`(1 pair)`, `(3 per)`) as *potential* rather than mismatch. Thresholds are
configurable and recorded in the report.

### 7.4 Terminology relationships
`Relationship { id, canonical, aliases[], scope: global | product-family | SKU, doc_types[], item_anchors[],
provenance: manual | learned, created_by, created_at, active, notes }`. CRUD in the UI; Excel/CSV import-export
(load their existing synonym lists in one step); every run records the dictionary version used. The engine
also **mines suggestions** from a batch (same BOM item repeatedly sitting next to the same label term across
SKUs) and offers them for one-click approval.

### 7.5 Discrepancy taxonomy
`QTY_MISMATCH`, `DESC_MISMATCH`, `MISSING_IN_LABEL`, `MISSING_IN_BOM`, `MISSING_IN_DRAWING`,
`EXTRA_ON_DRAWING`, `REF_PARENT_MISMATCH`, `PCO_CHANGE_NOT_APPLIED`, `PCO_QTY_SEQ_MISMATCH`,
`BOM_MISSING_FOR_AFFECTED_CODE`, `UNEXPECTED_LABEL_CHANGE`, `EXPECTED_CHANGE_ABSENT`, `DRAWING_REV_MISMATCH`,
`AMBIGUOUS_MATCH`, `LOW_EXTRACTION_CONFIDENCE`. Each has severity (blocker / major / minor / info) and a
default "requires validation" rule.

### 7.6 Excel report
Sheets: **Summary** (per SKU counts by class, status, reviewers, dates, effort estimate) · one sheet per check
type · **Action Items** · **Relationships used** (snapshot) · **Run metadata** (files + SHA-256, tool version,
thresholds, timestamp) · **Manual checklist** (dot sticker etc.) · **Audit log**.
Row columns: Row ID · SKU · Check · Source A (file, page, item #, description, qty) · Source B (same) ·
Normalised A/B · Classification · Score · Relationship applied · Discrepancy type + detail · Severity ·
Requires validation · AI note · Reviewer 1 decision / comment / name / date · Reviewer 2 same · Final status ·
Link to source page. Conditional formatting, frozen headers, filters, data-validation dropdowns for decisions,
re-importable.

### 7.7 Reviewer workflow
1. Drop a folder/zip → tool groups files by SKU, shows coverage ("PCO lists 6 affected codes, BOM present for 5").
2. Run → dashboard: auto-cleared vs needs-review; results grid with filters; side-by-side evidence with
   highlighted source regions; extraction-verification view (raw page vs extracted table).
3. Accept / override / confirm-discrepancy per row, bulk-accept exact matches, "save as relationship".
4. Independent reviewer opens the run in **blind mode** (facilitator's decisions hidden until they submit),
   then differences are surfaced for discussion — mirrors the cross-check meeting.
5. Export Excel, annotated BOM PDF, action items, BCMM draft. After fixes, re-run → resolved items linked to
   action-item IDs (verify & close).

### 7.8 Business-case calculator
Summary sheet computes from the actual run: rows auto-cleared, rows reviewed, estimated minutes saved per SKU
using their baseline (60 min/SKU/reviewer, $37.50/h, 100 SKUs, 20 projects/yr). If ~80% of rows auto-clear
and review drops to ~15 min/SKU, that is ~75% reduction vs. the 50% target — shown live, not claimed.

## 8. Priority stack (what must be flawless vs. what wows)

**P0 — must be flawless (mandatory + 60% of the score):** BOM/label/PCO/drawing parsers on PDF + Excel;
match ladder L0–L3 with explanations; five checks; relationship CRUD + import/export; reviewer decisions;
Excel report with traceability; batch grouping; CLI; golden dataset + accuracy harness.
**P1 — differentiators:** learned relationships + batch mining; evidence bounding boxes + highlights;
annotated BOM PDF; blind two-reviewer mode; coverage checks; run reproducibility; effort dashboard; OCR fallback.
**P2 — wow if time:** semantic layer; optional LLM adjudication + vision extraction for scanned labels;
action items + BCMM draft; verify & close re-run diff; Docker + one-command install; roadmap to SharePoint/Azure.

## 9. Default assumptions (override if wrong — none of these block starting)

| Topic | Default | If different |
|---|---|---|
| Sample data | No real files yet → build a realistic synthetic family (8–10 SKUs) mirroring R30460 BOM, kit-contents label, EN/ES drawing, FM00835 PCO, one scanned label; ground truth JSON | Real files replace/augment the synthetic set; parsers tuned on them at checkpoint 1 |
| Runtime | Runs on a reviewer laptop or a shared internal machine; pip/venv, no admin rights; Docker optional | Azure/M365 deployment is a wrapper on the same API later |
| LLM policy | Offline by default; LLM layer off unless enabled with Anthropic Claude or Azure OpenAI keys | If allowed, we demo vision extraction of a scanned label as the wow moment |
| Redlines | Support PDF annotations and red-text overlays; hand-drawn scans fall back to the PCO form as source of proposed values | Add red-region OCR if scans are the norm |
| Stack | Python 3.12, FastAPI, pydantic, pymupdf, pdfplumber, openpyxl, rapidfuzz, rapidocr-onnxruntime, SQLite; React + Vite + Tailwind UI; python-docx for BCMM draft; sentence-transformers optional | Streamlit UI if the team prefers speed over polish |
| Scope | All five checks; depth order BOM↔Label, PCO↔BOM, BOM↔Drawing, Label↔Drawing, Old↔New | — |

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Synthetic data differs from real formats | Get real (redacted) sets at checkpoint 1; parsers are per-doc-type and fixture-tested, so swapping is cheap |
| Multi-column label extraction garbles lines | Word-bbox column clustering; `N Each -` anchors; vision-LLM fallback |
| Over-flagging drowns reviewers | Non-physical BOM categorisation; tuned thresholds; auto-clear bucket; severity |
| Hand-drawn redlines on scans | Use the PCO form as the authoritative list of proposed changes |
| LLM not allowed on corporate data | Engine is complete without it |
| Scope creep in 4 weeks | Priority stack above; P0 complete by checkpoint 2 |

## 11. Suggested 4-week plan

- **Week 1 (7–13 Sep)** — synthetic dataset + ground truth, canonical model, BOM + label parsers, match ladder
  L0–L3, Excel report v1, CLI, accuracy harness. *Checkpoint 1: BOM↔Label end-to-end on 3 SKUs; ask owners for
  real files + synonym list.*
- **Week 2 (14–20 Sep)** — relationships store + UI, PCO + drawing parsers, checks 2–4, batch grouping,
  coverage checks, review decisions. *Checkpoint 2: four checks, batch of 8 SKUs, editable relationships,
  owners review classifications on their documents.*
- **Week 3 (21–27 Sep)** — evidence highlighting, blind two-reviewer mode, annotated PDF, learned
  relationships + mining, old↔new label diff, OCR fallback, semantic layer. *Checkpoint 3: full flow; demo
  dry run with owners.*
- **Week 4 (28 Sep–5 Oct)** — accuracy tuning on real/golden set, dashboard + business calculator, action
  items + BCMM draft, install script, docs, video, rehearsed demo.

## 12. Demo storyline (10 minutes)

1. The manual process (slide 7): 60 minutes, two pens, a tracker.
2. Drop a folder for 8 SKUs → grouped; one missing BOM flagged immediately.
3. Run → summary: e.g. 300 comparisons, 240 auto-cleared, 40 potential, 15 mismatches, 5 missing; accuracy
   panel against the golden set.
4. Open `TAPE ANCHOR PER-Q-CATH` ↔ `Surgical Tape`: evidence highlighted on both pages, accept, "save as
   relationship".
5. Re-run SKU #2: same pair now **Equivalent** automatically; mined suggestions appear.
6. A real discrepancy (qty 2 vs 1) and a PCO change not applied — severity, action item created.
7. Independent reviewer logs in blind, decides, differences surfaced.
8. Export: Excel (walk the columns, hashes, relationship snapshot), annotated BOM PDF with coloured check
   marks, BCMM draft.
9. Terminology manager: remove a relationship, re-run, classification changes live.
10. Close on the calculator: minutes saved per SKU → hours per project → dollars per year, from this run.

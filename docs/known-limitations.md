# Known limitations

Kaizen supports explained review, not automatic engineering release. Synthetic accuracy, source extraction
parity, mapping coverage, reviewer approval and measured real-data accuracy are different claims.
See [real-data validation](real-data-validation.md) for the scope of the local evidence.

## Documents and extraction

- Inputs are PDF, XLSX/XLSM and CSV in supported BOM/PCO layouts, plus PDF labels/drawings. Word is unsupported.
- Scanned PDFs need an installed offline OCR engine. Missing/unreadable pages and uncertain values produce
  warnings or review-required results. Native text can also be wrong; source pages remain authoritative.
- Drawing text/callouts are extracted. Pictured component identity, leader endpoints, placement, orientation
  and cavity occupancy are not verified. Drawings are not a component quantity source.
- Supported PDF text/FreeText annotations do not establish handwritten/scanned edits. The marked-up
  attachment batch, ticks and strikeouts are outside the agreed clean-document validation scope.
- Case-label checks and layouts without representative fixtures remain manual. Unknown formats/layouts
  need source validation and suitable parser fixtures rather than assumptions.

## Matching and findings

- Similarity/component scores are not probabilities. Typed candidates recover terse wording and apply
  numeric/type guards, but omitted specifications remain unknown. Drawing alternatives remain alternatives.
- Potential and Unmapped are review outcomes, not confirmed defects. Even equal printed quantities can
  leave a pack/pair basis unresolved. Confirm actual unit bases from approved specifications.
- Ordinary live pairings use one-to-one assignment. Inferred assemblies retain possible members as
  review proposals; approved per-unit allocations and verified component specifications are separate facts.
- Base labels may require applicable overlabels. Final artwork/configuration is needed before asserting
  saline/scissors or other configuration defects.
- Drawing applicability needs released source evidence. An explicitly conflicting drawing withholds
  component findings; a missing reference is not permission to assume an engineering release.
- Terminology is versioned, scoped and item-anchored. It cannot equate configurations, assemblies,
  ambiguous variants or known conflicting specifications. Existing runs retain their snapshots.
- The potential/floor/ambiguity thresholds remain recorded run settings, not proof of generalization.
  Do not tune them to make one delivery pass. Semantic/external AI suggestions remain optional.
- A rights-managed relationship workbook needs an authorized readable export; Kaizen does not remove
  organizational protection. See [relationship imports](relationship-import.md).

## Review and learning

- Registration is immediate for allowed domains but does not prove email ownership. Sessions do not
  expire automatically. Broader access needs an approved identity/session policy; see [security](security-review.md).
- Shared authentication alone does not synchronize local workspaces. Account roles, files, terminology,
  decisions and learning artifacts remain in the configured workspace.
- The website uses shared decisions and approvals; historical two-reviewer records remain compatible.
  Reviewer self-approval is explicit. Training truth still requires independent administrator verification.
- Only eligible, current, independently verified annotations enter learning datasets. Drawing examples
  need verified applicability. Small or missing held-out sets show Not measured/unqualified results.
- Candidate rules run separately against saved parsed sources. They are not automatically promoted and
  do not fine-tune an external foundation model. Passing the sample gate is not product-wide validation.
- Browser uploads/copies use distinct run IDs. Engine/CLI reproducibility also depends on extraction
  output, checker/parser versions, terminology and thresholds; source hashes must be compared explicitly.
- Timed effort measures opening-to-decision intervals between 5 seconds and 15 minutes, uses a median
  after ten observations, and cannot see work outside the app. Business-case projections retain assumptions.

## Reporting and deployment

- Summary Excel contains totals/status and attention rows; use Complete details for all comparisons and
  audit evidence. Both support decisions/comments on SKU worksheets. Editing engine cells does not
  update source documents or original recommendations. Workbooks remain bound to their run IDs.
- Imports skip stale/conflicting decisions unless explicitly forced, are attributed to the signed-in
  reviewer and invalidate changed approvals. Review edits do not replace independent ground truth.
- XLSX text is literal; CSV terminology exports escape formula-like values. Spreadsheet BOMs have no
  source-page geometry and use a separate annotated review page where supported.
- A disappeared comparison is reported as gone, not fixed. Diffing an unchanged relocated copy does not
  imply that its documents changed.
- Render has not been deployed. Docker/Render configuration prepares one worker with persistent storage;
  Docker OCR parity, hosted operation, backups and access readiness require validation before launch.
- No regulatory or quality-system validation claim is made.

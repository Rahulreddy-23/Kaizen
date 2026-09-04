# Known limitations (honest list)

Measured on synthetic documents modelled on the brief. None of the accuracy numbers are claims about real
JDE / MasterControl output, which has not been available.

## Extraction
- **OCR** runs only if `rapidocr-onnxruntime` is installed; otherwise image-only pages are reported and skipped.
  OCR is wired for labels; scanned BOM prints and drawings are reported, not read.
- **Hand-drawn or scanned redlines** are not read. PDF FreeText annotations are captured and used by the
  PCO ↔ BOM check; hand annotations are not.
- **Truncated ERP descriptions** (JDE cuts at a fixed width, e.g. `PRODUCING LABELS ON THE`) are not
  prefix-matched; a truncated last token lowers similarity.
- **Case labels** are not parsed; the manual checklist carries the case-label check.
- Parsers are keyed on the layouts in the brief (header words, `N Each -` starters, title-block labels).
  Other layouts will need fixtures and, possibly, parser variants.

## Matching
- Fuzzy pairs whose BOM tokens all appear in a long label line score 1.0 but remain POTENTIAL by design
  (never auto-cleared). On the golden set that is ~80 of ~1,100 rows; the learning loop converts confirmed
  ones into relationships so the next SKU auto-clears them.
- Thresholds (0.85 potential, 0.60 floor, 0.05 ambiguity) were chosen on synthetic data and are recorded in
  every run; they must be re-tuned on real documents.
- Semantic matching (L4) needs a locally installed embedding model and is off by default; AI adjudication (L5)
  needs explicit opt-in and an API key and only produces labelled suggestions.

## Checks
- Drawing checks are presence/identity only (by design: the drawing is not a quantity source).
- The drawing reference row requires a BOM line mentioning the drawing number; otherwise it asks the reviewer.
- Old ↔ New label expectations come only from PCOs in the same set; change instructions in other forms are
  not read.
- PCO affected codes must match BOM parent items exactly.

## Review workflow
- Reviewer identity, slot and blind mode are a server-side session and cannot be changed from the browser,
  but this is identification, not authentication: anyone with access to the machine can sign in under any
  name. A shared deployment needs SSO. The session cookie is not marked `Secure` because the local server
  is plain HTTP.
- Sessions do not expire on their own; end one with "Sign out" or `kaizen review sessions --end <name>`.
- Decisions live in the local workspace database; there is no multi-user server. Re-running the same inputs
  with the same code and terminology reproduces the same run id and row ids, so decisions re-attach; a code
  change produces a new run id and decisions are not carried over automatically.

## Reporting
- Annotated BOM marks need page geometry; spreadsheet BOMs get a separate review page instead.
- The Excel workbook is generated, not round-tripped: edits made in Excel are not re-imported yet
  (reviewer decisions are captured through the UI/API).

## Not regulatory-compliant
This is a hackathon prototype. It is deterministic, auditable and offline, but it has not been validated
under a quality system and makes no compliance claim.

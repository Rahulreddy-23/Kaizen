# HTTP API contract

The local server is `http://127.0.0.1:8765`; the UI uses relative `/api` URLs on the same origin.
Render deployment is pending. Responses are JSON unless a download/image is specified.

Contract version: **3**. `/api/health` includes `restart_required` when the running server no longer
matches the source. Restart the server after backend changes; the UI refuses an incompatible contract.

Request models live in [payloads.py](../src/kaizen/api/payloads.py) and
[learning.py](../src/kaizen/review/learning.py). Full response types are in
[types.ts](../ui/src/types.ts); implementation is [app.py](../src/kaizen/api/app.py).

## Authentication and errors

Signup creates an approved regular profile for an allowed domain (`bd.com` by default). Pending profiles
are approved after valid sign-in; revoked profiles remain blocked. This verifies a password account, not
email ownership. Local passwords use salted scrypt; an explicitly configured provider can check them
instead. See [accounts/provider setup](hosted-collaboration.md).

The HttpOnly `kaizen_session` cookie supplies the actor. Current HTTP sessions use `slot: 1`, `blind: false`;
client actor/slot/blind fields do not choose identity or bypass visibility. Sessions do not expire on their
own. Hosted configuration enables Secure cookies; mutations with a supplied cross-origin Origin are refused.

| Status | Meaning |
| --- | --- |
| 400 | Invalid business input, unsupported/unusable document or import content. |
| 401 | Missing/invalid session or credentials. Wrong password and unknown account share the same sign-in error. |
| 403 | Insufficient permission, revoked/pending provider condition, or forbidden operation. |
| 404 | Unknown or inaccessible run/item/source. Inaccessible run IDs do not reveal existence. |
| 409 | Duplicate account or stale decision/annotation version. |
| 413 | Upload exceeds its size limit. Document-run uploads are limited to 250 MB in total. |
| 422 | Invalid typed payload/query, including unsupported Excel detail level. |
| 429 | Rate limiting; local accounts lock out for 15 minutes after ten consecutive failed attempts. |
| 500 / 503 | Unexpected error with server-log reference / unavailable account provider. |

| Method | Path | Input / result |
| --- | --- | --- |
| POST | `/api/auth/signup` | `{email, password}`; registers a regular account. Allowed domain and minimum ten-character password are checked. |
| POST | `/api/auth/signin` | `{email, password}`; session with reviewer, role and cookie. |
| POST | `/api/sessions` | Legacy creation is not a sign-in bypass; authenticated calls are refused with 403. |
| GET | `/api/sessions/current` | `{session: {...} or null, blind_review_policy, accounts}`; account provider is local or supabase. |
| DELETE | `/api/sessions/current` | Ends the current session and clears its cookie. |
| GET | `/api/health` | Public `{status, version, api_contract, restart_required, hosted}`. |

There are no confirmation/reset-email endpoints. Provider password recovery needs authorized operator
help. Local account reset uses the CLI; prior decisions retain their recorded email identity.
`KAIZEN_ALLOWED_DOMAINS` controls domains; `KAIZEN_SUPABASE_URL` and `KAIZEN_SUPABASE_KEY` override
stored provider selection and must be set together. Only publishable/legacy anon provider keys are accepted.

## Permissions, accounts and sharing

Except authentication/current-session/health handling, API access requires a valid approved session.
Run owners manage sharing and rename; owners/editors mutate, copy and download review exports. Viewers
can browse results and source previews. Administrator status does not reveal private runs.
Terminology writes and audit/user administration require an application administrator. Learning
verification, candidate evaluation and dataset exports additionally require Edit access to the run.

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/profiles` | Approved profile email choices. |
| GET | `/api/admin/users` | Administrator-only profile list. |
| PATCH | `/api/admin/users/{email}` | `{status?, is_admin?}`; manages roles/revocation, protecting the last approved administrator. |
| GET | `/api/runs/{run_id}/sharing` | Owner-only share list. |
| PUT | `/api/runs/{run_id}/sharing` | Owner `{email, permission: "view" or "edit" or null}`; null revokes the share. |
| PATCH | `/api/runs/{run_id}` | Owner `{name}`; trimmed 1–120 characters. |
| POST | `/api/runs/{run_id}/copy` | Private independent run owned by the actor. Sharing/approvals do not transfer. |
| GET | `/api/runs/{run_id}/download.zip` | Sources, portable run JSON, history and editable workbook. Downloading alone does not register a new run. |

## Runs and original/current results

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/runs` | Accessible run records with names, ownership, permissions, original summary and current review progress. Missing saved runs are marked unavailable. |
| POST | `/api/runs/from-path` | `{path, name?}`; administrator-only and disabled in hosted mode. |
| POST | `/api/runs/upload` | Multipart `files[]`, optional `name`; relative filenames preserve folder structure. PDF/XLSX/XLSM/CSV, safe paths and total size are validated. |
| POST | `/api/demo/load` | Loads the synthetic fixture run. |
| GET | `/api/runs/{run_id}` | Run summary, groups, source counts, warnings, thresholds, terminology version and review progress. |

Uploads/copies receive distinct web run IDs. Source hashes and metadata identify what actually changed;
do not treat different run IDs as different source content. Run names are descriptive, not identifiers.

Run summaries distinguish original `counts`, `needs_validation`, `auto_cleared` and `per_check` from current
`review_progress`/`state_counts`. The current snapshot includes pending, awaiting_review, awaiting_approval,
approved, needs_information, unresolved_rows, confirmed_discrepancies, blockers, low_confidence_rows and
discrepancy row counts. Aggregation covers the complete run, not just the displayed queue page.

Saving a decision awaits approval. An approved Exact/Equivalent acceptance or override clears its current
finding. Approving a confirmed discrepancy completes review while retaining the finding. Needs-more-information
remains pending even after approval. Editing an approved row invalidates approval and retains history.

## Queue and evidence

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/runs/{run_id}/results` | Filters below; `{total, offset, limit, rows[], viewer}`. |
| GET | `/api/runs/{run_id}/results/{row_id}` | Full original result/evidence, decisions, effective classification, state/final, revision, owner, permission, history, action items and `can_save_relationship`. |
| GET | `/api/runs/{run_id}/documents` | Document identity/type, paths/hashes, parser, SKU, pages, item counts and warnings. |
| GET | `/api/runs/{run_id}/documents/{doc_id}/items` | Extracted source items with retained page/evidence details. |
| GET | `/api/runs/{run_id}/documents/{doc_id}/pages/{page_no}` | PNG for a 1-based PDF page; optional `highlight={row_id}`, `dpi=110`. Spreadsheet sources have no source-page image. |

Queue parameters: `check`, `sku`, `classification` (current), `engine_classification` (original), `severity`,
`discrepancy`, `needs_validation`, `unresolved`, `state`, `role`, `search`, `limit` (default 500, 1–5000)
and `offset` (nonnegative). The UI requests 100 rows per page. Legacy viewer/blind parameters do not
override a signed-in session. Search covers SKU, explanations and both sides' descriptions/item numbers.
`needs_validation` filters current pending review; severity filters current severity. With `unresolved=true`,
discrepancy filters current findings; otherwise it filters original discrepancies. UI `nv=0` clears its
pending-only default. Queue order prioritizes severity, ambiguity, potential and low-confidence rows.

Each queue row keeps `engine`, `effective_classification`, `decisions`, `state`, `final`, `pending_review`,
`unresolved`, `current_severity`, `current_discrepancies`, source summaries `a`/`b`, original discrepancies
and action-item links. Decisions are keyed by slot for compatibility; HTTP uses the shared slot 1 workflow.

Evidence keeps file/hash, document/item IDs, raw description/text, quantity, unit, locator, confidence,
attributes and page/bbox when available. PDF coordinates use 72-point units; rendered images scale by
`dpi/72`. Duplicate/source copies keep their own references. Human-readable UI labels preserve API codes.

`MISSING` displays as **Unmapped**. It does not prove physical absence. Review-required types include
`QUANTITY_BASIS_UNCONFIRMED`, `LABEL_CONFIGURATION_REVIEW` and `DRAWING_APPLICABILITY_UNCONFIRMED`.
Component/assembly candidates remain Potential with source evidence; missing specifications are unknown.

## Decisions and terminology suggestions

| Method | Path | Input / result |
| --- | --- | --- |
| POST | `/api/runs/{run_id}/decisions` | `{row_id, decision, comment?, override_classification?, expected_revision}`; records the shared decision and clears prior approval. |
| POST | `/api/runs/{run_id}/finalize` | `{row_id, final_decision, expected_revision, confirm_self_approval?, note?}`; approves the saved current decision. |
| POST | `/api/runs/{run_id}/bulk-accept` | `{}`; accepts eligible clean rows, not approval of the whole run. |
| POST | `/api/runs/{run_id}/relationships/from-row` | Administrator with Edit access: `{row_id, scope?, anchor?, canonical?, aliases?, doc_types?, notes?}`. |
| GET | `/api/runs/{run_id}/terminology-worklist` | Ranked identity suggestions, projected rows cleared and top-five/top-ten totals. |
| GET | `/api/runs/{run_id}/mining` | Optional `min_skus=2`; repeated suggestions with evidence/confirmations/contradictions. |
| POST | `/api/runs/{run_id}/mining/approve` | Administrator with Edit access: `{a_key, b_key, scope?, anchor?, notes?}`; versioned relationship. |
| POST | `/api/runs/{run_id}/mining/reject` | Administrator with Edit access: `{a_key, b_key, note?}`. |

Decision kinds: `ACCEPT`, `OVERRIDE`, `CONFIRM_DISCREPANCY`, `NEEDS_MORE_INFORMATION`. An override needs
its classification. Send the displayed revision; stale changes return 409. Approving the decision author's
or owner's own run/decision needs explicit self-approval confirmation, recorded separately from ground truth.

`can_save_relationship` is false for assemblies, configurations, ambiguity, explicit alternatives and
incompatible types/specifications. The UI and endpoint use the same eligibility guard; invalid requests
return 400. Held-out SKU examples cannot become learned training terminology. Suggestions never create rules automatically.

## Closed testing

All paths retain normal run access. Only the owner enables testing. Editors can annotate; verification,
dataset exports and candidate evaluation need an administrator with Edit access. Verification must use a different
actor from the annotation/applicability author. See [learning safeguards](closed-testing.md).

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/runs/{run_id}/learning` | Enrollment, immutable SKU splits, tasks, coverage, evaluation and durable job state. |
| POST | `/api/runs/{run_id}/learning/enable` | Enroll before learning; reserve evaluation identities. |
| GET | `/api/runs/{run_id}/learning/rows/{row_id}` | Current annotation/split, source choices, suggested attributes and review revision. |
| PUT | `/api/runs/{run_id}/learning/rows/{row_id}` | `{expected_version, review_revision, verdict, classification, expected_a_ids[], expected_b_ids[], discrepancies[], attributes, assembly_quantities, note}`. |
| POST | `/api/runs/{run_id}/learning/rows/{row_id}/approve` | `{expected_version, approve, note?}`; verifies/rejects and queues candidate rebuild. |
| PUT | `/api/runs/{run_id}/learning/drawings/{sku}` | `{expected_version, doc_id, applicability, released_revision, release_reference, note}`. |
| POST | `/api/runs/{run_id}/learning/drawings/{sku}/approve` | `{expected_version, approve, note?}`; independent applicability verification. |
| GET | `/api/runs/{run_id}/learning/export.json` | `split=train` or `evaluation`; separate verified dataset. |
| GET | `/api/runs/{run_id}/learning/observations.json` | Raw decision histories/timing, not ground truth. |
| POST | `/api/runs/{run_id}/learning/shadow` | Rebuild/evaluate the offline candidate; returns frozen report. |

Verdicts: `CORRECT_PAIR`, `INCORRECT_PAIR`, `GENUINE_DISCREPANCY`, `UNRESOLVED`.
Attributes are keyed by selected item IDs and support component_type, dimensions_mm, gauge,
concentration_pct and pack_quantity. Assembly quantities are positive allocations per label unit.
Applicability is `CONFIRMED_RELEASED`, `NOT_APPLICABLE` or `UNCONFIRMED`; confirmed release needs a revision/reference.

Unresolved/stale/unverified labels are excluded. Drawing samples need verified exact-source applicability.
Verified changes schedule a durable, coalescing rebuild; restart resumes pending work. Candidates use saved
parsed sources and remain separate from live results, decisions and shared terminology.

## Follow-up and business estimates

| Method | Path | Input / result |
| --- | --- | --- |
| POST | `/api/runs/{run_id}/action-items` | `{row_id, owner?}`; actor from session. |
| GET | `/api/action-items` | Optional `status`, `run_id`; only accessible runs, with permission. |
| PATCH | `/api/action-items/{ai_id}` | Edit access: `{status?, owner?, note?}`. |
| POST | `/api/runs/{run_id}/verify-and-close` | Optional `against={earlier_run_id}`; requires Edit on both selected runs. |
| GET | `/api/runs/{run_id}/business-case` | Validated finite assumptions and current estimates/projection; parameters below. |
| GET | `/api/runs/{run_id}/diff` | Required `against`; source changes plus resolved/new/still_open/changed/unchanged/gone/not_covered counts and rows. |

Business parameters: baseline_minutes_per_sku (>0), hourly_rate (>=0), skus_per_project (integer >=1),
projects_per_year (integer >=0), reviewers (integer >=1), minutes_per_validation_row/minutes_per_cleared_row
(>=0), target_reduction_pct (0–100). Opening a row as an editor starts effort timing; decisions between
5 seconds and 15 minutes count. The business estimate uses a median after ten timed decisions; bulk
acceptance and imports do not count as measured effort. Assumptions remain visible below that sample size.
A disappeared comparison is gone, not resolved. Unchanged relocated copies are not reported as all documents added/removed.

## Downloads and decision imports

All review downloads require Edit access. Source-page previews remain available to viewers.

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/runs/{run_id}/export.xlsx` | `detail=summary` (default) or `complete`; per-SKU XLSX download. Invalid detail returns 422. |
| GET | `/api/runs/{run_id}/annotated-bom/{doc_id}` | PDF; `X-Kaizen-Fallback` marks a geometry fallback and `X-Kaizen-Marks` reports mark count. |
| GET | `/api/runs/{run_id}/certificate.pdf` | Optional `sku`; one page per SKU, with hashes, review counts and open action items. |
| POST | `/api/runs/{run_id}/decisions/import` | Multipart `file`, `dry_run=false`, `force=false`; validated decision round trip. |

Summary includes check totals, current status and attention rows. Complete details includes every
comparison, original/source evidence, approvals and supporting audit sheets. Both use SKU worksheets
and importable decision/comment columns. XLSX business text is stored as literal text. Filenames include
the selected detail. The CLI/portable workbook layouts remain import-compatible.

Imports require this run's metadata, stable row IDs and valid decisions. Only the session's reviewer
columns are applied. Values changed after export are conflicts unless explicitly forced; original engine
columns are ignored. Dry runs apply no decisions. Responses distinguish applied/unchanged rows, conflicts,
invalid cells and unknown rows. Changed decisions invalidate approvals and eligible learning labels.

## Shared terminology

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/terminology` | Optional `search`, `scope`, `all`; relationships with usage. |
| GET | `/api/terminology/export.xlsx` | Kaizen-format terminology workbook. |
| POST | `/api/terminology/inspect` | Administrator multipart `file`, optional `sheet`, `header_row`; columns, samples, proposed mapping and SHA-256. |
| POST | `/api/terminology/import` | Administrator multipart `file`, optional sheet/header/column_map/default_scope/dry_run/expected_version. |
| POST | `/api/terminology` | Administrator `{canonical, aliases[], scope, doc_types[], item_anchors[], provenance?, notes?}`. |
| GET | `/api/terminology/{rel_id}` | Relationship detail. |
| PUT | `/api/terminology/{rel_id}` | Administrator canonical/aliases/scope/doc_types/item_anchors/notes and version-history note. |
| POST | `/api/terminology/{rel_id}/deactivate` | Administrator; deactivates and versions history. |
| POST | `/api/terminology/{rel_id}/activate` | Administrator; reactivates and versions history. |
| DELETE | `/api/terminology/{rel_id}` | Administrator; history remains. |
| GET | `/api/terminology/{rel_id}/history` | Version history. |
| GET | `/api/audit` | Administrator; optional `limit=200`. |

Scopes are global, family:<prefix> or sku:<code>; item anchors and document types further limit identity.
Mapping keys include ID, Canonical, Aliases, Scope, Doc Types, Item Anchors, Provenance, Created By,
Active and Notes. Uploaded author fields never override the authenticated actor. Any invalid mapped row
blocks the entire import. Repeating identical no-ID rows preserves existing rules/inactive status.
Formula cells require values-only exports; unreadable protected workbooks produce an actionable 400.
See [authorized import instructions](relationship-import.md) for column mapping, previews and provenance.

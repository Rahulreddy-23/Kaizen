# HTTP API contract

The local server is `http://127.0.0.1:8765`; the UI uses relative `/api` URLs on the same origin.
The Render pilot uses the same API contract. Responses are JSON unless a download/image is specified.

Contract version: **3**. `/api/health` includes `restart_required` when the running server no longer
matches the source. Restart the server after backend changes; the UI refuses an incompatible contract.

Request models live in [payloads.py](../src/kaizen/api/payloads.py) and
[learning.py](../src/kaizen/review/learning.py). Full response types are in
[types.ts](../ui/src/types.ts); implementation is [app.py](../src/kaizen/api/app.py).

## Quick view

`GET /api/runs/{run_id}/quick-view` is a read-only, run-access-protected projection. Query parameters:
`sku` (defaults to first saved group), `view=components|text`, `status=all|compared|matched|attention|neutral`,
`search`, `offset` (non-negative), `limit` (1–500, default 100). It returns selected `sku`, saved `groups`,
associated `documents` with page counts/full-text availability, unfiltered status `counts`, filtered
`total`, pagination and `rows`. Each row has three nullable cells (`BOM`, `LABEL`, `DRAWING`) containing
source `items` (evidence plus ID), its `status`, and recorded `checks` with current findings and review state.
No new pairings, extraction, decisions or approvals are written. Text-mode rows follow independent source
order; positions across columns do not mean equivalence. Missing counterparts/exemptions cannot turn green
from their stored classification alone. Invalid SKU returns 404. View-only access is sufficient.
`can_export` indicates whether the current session may download a comparison workbook.

`GET /api/runs/{run_id}/quick-view/export.xlsx?sku=...` downloads that SKU; omitting `sku` includes all
saved SKU groups. Requires owner/editor access and a non-blind session. One comparison sheet per SKU,
with original extracted source details on Sources. Includes every entry regardless of screen filters or
pagination, using one current review snapshot. No reparsing or decision changes. Private/no-store;
each request owns a temporary file deleted after streaming. This value-only workbook is not a decision import.

## Authentication and errors

Signup requires an unexpired, unrevoked, one-use invitation matching the `@bd.com` address. The invitation
creates an approved regular profile. Signing in never promotes missing, pending or revoked profiles.
Invitation delivery requires a trusted channel; it is not automatic email ownership verification. Local passwords use salted scrypt; an explicitly configured provider can check them
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
| 413 | Upload exceeds its size limit. Document uploads are limited to 250 MB per run (one three-document set). |
| 422 | Invalid typed payload/query, including unsupported Excel detail level. |
| 429 | Rate limiting; local accounts lock out for 15 minutes after ten consecutive failed attempts. |
| 500 / 503 | Unexpected error with server-log reference / unavailable account provider. |

| Method | Path | Input / result |
| --- | --- | --- |
| POST | `/api/auth/signup` | `{email, password, invitation}`; consumes a valid email-bound invitation and registers a regular account. BD domain and minimum ten-character password are checked. Invalid invitations return 403. |
| POST | `/api/auth/signin` | `{email, password}`; session with reviewer, role and cookie. |
| POST | `/api/sessions` | Legacy creation is not a sign-in bypass; authenticated calls are refused with 403. |
| GET | `/api/sessions/current` | `{session: {...} or null, blind_review_policy, accounts, registration: "invite_only"}`; account provider is local or supabase. |
| DELETE | `/api/sessions/current` | Ends the current session and clears its cookie. |
| GET | `/api/health` | Public `{status, version, api_contract, restart_required, hosted}`. |
| GET | `/api/changes` | Authenticated opaque revision for saved changes and candidate-job state. No document content, run IDs or audit details. Private/no-store. Reads and session last-seen updates do not change it. |

There are no confirmation/reset-email endpoints. Provider password recovery needs authorized operator
help. Local account reset uses the CLI; prior decisions retain their recorded email identity.
The allowed domain is `bd.com`; `KAIZEN_SUPABASE_URL` and `KAIZEN_SUPABASE_KEY` override
stored provider selection and must be set together. Only publishable/legacy anon provider keys are accepted.

## Permissions, accounts and sharing

Except authentication/current-session/health handling, API access requires a valid approved session.
Run owners manage sharing, rename, delete and restore; owners/editors mutate, copy and download review exports. Viewers
can browse results and source previews. Administrator status does not reveal private runs.
Approved reviewers create/adopt terminology. Shared updates/imports/deactivation/deletion and audit/user administration require an administrator. Learning
verification, candidate evaluation and dataset exports additionally require Edit access to the run.

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/profiles` | Approved profile email choices. |
| GET | `/api/admin/invitations` | Administrator-only metadata; never returns codes/hashes. |
| POST | `/api/admin/invitations` | Administrator `{email, expires_hours?: 72}` (1–168); returns one-time `code` and metadata. Reissuing revokes prior outstanding codes. |
| DELETE | `/api/admin/invitations/{id}` | Administrator revokes an unused code. Account access is managed separately. |
| GET | `/api/admin/users` | Administrator-only profile list. |
| PATCH | `/api/admin/users/{email}` | `{status?, is_admin?}`; manages roles/revocation, protecting the last approved administrator. |
| GET | `/api/runs/{run_id}/sharing` | Owner-only share list. |
| PUT | `/api/runs/{run_id}/sharing` | Owner `{email, permission: "view" or "edit" or null}`; null revokes the share. |
| PATCH | `/api/runs/{run_id}` | Owner `{name}`; trimmed 1–120 characters. |
| DELETE | `/api/runs/{run_id}` | Owner moves the run to Deleted runs; retains documents, reviews and sharing for recovery. All normal run routes become inaccessible. |
| POST | `/api/runs/{run_id}/restore` | Only the original owner restores a deleted run, including its prior sharing. |
| DELETE | `/api/runs/{run_id}/permanent` | Original owner only; run must already be deleted. Body: `{"confirmation":"<run_id>"}`. Erases run-scoped review/learning data and unshared app-managed files. Returns `deleted` and `cleanup_pending`; pending file removal retries at startup. Conflicts (409) while run requests or closed-testing jobs are in flight. Copies, local original folders, shared files and approved terminology survive. |
| POST | `/api/runs/{run_id}/copy` | Private independent run owned by the actor. Sharing/approvals do not transfer. |
| GET | `/api/runs/{run_id}/download.zip` | Sources, portable run JSON, history and editable workbook. Downloading alone does not register a new run. |

## Runs and original/current results

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/runs` | Accessible run records with names, ownership, permissions, original summary and current review progress. Missing saved runs are marked unavailable. `deleted=true` instead lists only the actor’s deleted runs with `deleted_at`/`deleted_by` and stored summaries. |
| POST | `/api/runs/from-path` | `{path, name?}`; administrator-only and disabled in hosted mode. Returns `{runs: RunSummary[], failures: [{path, message}]}`. Every document folder becomes a separate run; nested folders are independent. Invalid sets are rejected before any runs are created; runtime failures report saved runs and failed paths. |
| POST | `/api/runs/upload` | Multipart `files`, optional `name`; one folder containing exactly one BOM, one label and one drawing. Three individually selected files use a synthetic folder prefix. Safe relative paths, readable document types and the 250 MB per-run limit are validated. Submit additional folders separately. |
| POST | `/api/demo/load` | Loads the synthetic fixture run. |
| GET | `/api/runs/{run_id}` | Run summary, groups, source counts, warnings, thresholds, terminology version and review progress. |

The upload, local-path and demo endpoints accept `?stream=true` to return `application/x-ndjson`.
Each line is `{type: "progress", percent: 0..100, stage}`, `{type: "result", data}` or
`{type: "error", status, detail}`. Percentages mark processing stages, rather than elapsed-time estimates;
100 means the requested runs have been saved. Stream errors occur after HTTP headers, so clients must
read terminal events and must not infer success from HTTP 200. An interrupted stream is not a safe
retry signal: refresh All runs first. JSON responses remain the default. Health `api_contract` is 4;
older cached clients must refresh and stale servers must restart.

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
| GET | `/api/runs/{run_id}/documents/{doc_id}/pages/{page_no}` | 1-based PDF page; optional `highlight={row_id}`, `dpi=110` (36–300), `format=png|jpeg` (default PNG; JPEG quality 92). Spreadsheet sources have no source-page image. Authorized on every request, including server memory-cache hits; responses remain private/no-store. |

Queue parameters: `check`, `sku`, `classification` (current), `engine_classification` (original), `severity`,
`discrepancy`, `needs_validation`, `unresolved`, `state`, `role`, `search`, `limit` (default 500, 1–5000)
and `offset` (nonnegative). The UI requests 100 rows per page. Legacy viewer/blind parameters do not
override a signed-in session. Search covers SKU, explanations and both sides' descriptions/item numbers.
`needs_validation` filters current pending review; severity filters current severity. With `unresolved=true`,
discrepancy filters current findings; otherwise it filters original discrepancies. UI `nv=0` clears its
pending-only default. Queue order prioritizes severity, ambiguity, potential and low-confidence rows.
Exempt rows remain available through the unfiltered queue, `role=exempt`, and direct row links.
Classification filters and `needs_validation=false` exclude them: their historical `EXACT` storage
value is an exemption, not a verified counterpart. The UI labels these rows “Not required by this
check”; they are excluded from auto-cleared counts and bulk acceptance.

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
| POST | `/api/runs/{run_id}/relationships/from-row` | Reviewer with Edit access: `{row_id, scope?, anchor?, canonical?, aliases?, doc_types?, notes?}`; explicitly approves and adopts that identity relationship. |
| GET | `/api/runs/{run_id}/terminology-worklist` | Ranked identity suggestions, projected rows cleared and top-five/top-ten totals. |
| GET | `/api/runs/{run_id}/mining` | Optional `min_skus=2`; repeated suggestions with evidence/confirmations/contradictions. |
| POST | `/api/runs/{run_id}/mining/approve` | Reviewer with Edit access: `{a_key, b_key, scope?, anchor?, notes?}`; versioned relationship. |
| POST | `/api/runs/{run_id}/mining/reject` | Administrator with Edit access: `{a_key, b_key, note?}`. |

Decision kinds: `ACCEPT`, `OVERRIDE`, `CONFIRM_DISCREPANCY`, `NEEDS_MORE_INFORMATION`. An override needs
its classification. Send the displayed revision; stale changes return 409. Approving the decision author's
or owner's own run/decision needs explicit self-approval confirmation, recorded separately from ground truth.

`can_save_relationship` is false for assemblies, configurations, ambiguity, explicit alternatives and
incompatible types/specifications. The UI and endpoint use the same eligibility guard; invalid requests
return 400. Held-out SKU examples cannot become learned training terminology. Suggestions never create rules automatically.

## Closed testing

All paths retain normal run access. Collection starts automatically for new owned runs, copies and
existing active owned runs on startup. Editors can annotate; verification,
dataset exports and candidate evaluation need an administrator with Edit access. Verification must use a different
actor from the annotation/applicability author. See [learning safeguards](closed-testing.md).

| Method | Path | Input / result |
| --- | --- | --- |
| GET | `/api/runs/{run_id}/learning` | Automatic collection status, setup_issue, immutable SKU splits, tasks, coverage, evaluation and durable job state. |
| POST | `/api/runs/{run_id}/learning/enable` | Compatibility endpoint: owner-only, idempotent enrollment/retry; no longer required by the UI. |
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
| GET | `/api/terminology` | Optional `search`, `scope`, `all`; relationships with `approved_by`, `approved_at`, `is_default`, `selected_version`, `enabled_version`, older `enabled_definition` when applicable, and usage scoped to accessible runs. |
| GET | `/api/terminology/export.xlsx` | Kaizen-format terminology workbook. |
| POST | `/api/terminology/inspect` | Administrator multipart `file`, optional `sheet`, `header_row`; columns, samples, proposed mapping and SHA-256. |
| POST | `/api/terminology/import` | Administrator multipart `file`, optional sheet/header/column_map/default_scope/dry_run/expected_version. |
| POST | `/api/terminology` | Approved reviewer `{canonical, aliases[], scope, doc_types[], item_anchors[], provenance?, notes?}`. |
| PUT | `/api/terminology/selections` | `{entries: [{id, version}], selected: true/false}` (1–5000); changes only the authenticated account. Atomic batch, duplicate IDs/stale/inactive additions return 409; missing entries 404. |
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

Terminology creation and explicit evidence/suggestion approval adopt that version for the actor. Successful
imports adopt active imported entries for the importer. Other accounts explicitly select entries. Uploads
use packaged defaults plus that uploader’s pinned selections; edits require re-adoption, deactivation and
deletion exclude future use globally. Existing runs/copies retain snapshots. Authors’ existing active terms
are adopted once on migration; removing them remains effective after restart.

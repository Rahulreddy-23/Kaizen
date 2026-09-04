# Kaizen Cross-Check — local API contract (for the reviewer UI)

Base URL when running `kaizen serve`: `http://127.0.0.1:8765`. All endpoints are local; no authentication
(reviewer identity is a name typed in the UI). JSON unless stated. Errors: 400 (invalid input), 404 (unknown id).

## Runs
| Method | Path | Body / params | Returns |
|---|---|---|---|
| GET | `/api/health` | | `{status, version, workspace}` |
| GET | `/api/runs` | | `[{run_id, created_at, input_root, tool_version, terminology_version, json_path, summary:{rows, skus, documents, needs_validation, EXACT, EQUIVALENT, POTENTIAL, MISMATCH, MISSING}}]` (flat classification keys; counts over all rows as registered) |
| POST | `/api/runs/from-path` | `{path}` (local folder) | run summary (below) |
| POST | `/api/runs/upload` | multipart `files[]`; each filename may include a relative path such as `sku-001/bom.pdf` (use `webkitRelativePath` for folder drops) | run summary |
| POST | `/api/demo/load` | | run summary (golden dataset) |
| GET | `/api/runs/{run_id}` | | run summary |

Run summary: `{run_id, timestamp, input_root, tool_version, skus, documents, documents_by_type:{BOM,LABEL,DRAWING,PCO}, unrecognised_files[], rows (all result rows), reviewable_rows (roles item + change), exempt_rows, header_rows_needing_validation (header/reference/coverage rows that need validation, e.g. REF mismatch or missing BOM), counts:{EXACT,EQUIVALENT,POTENTIAL,MISMATCH,MISSING} (reviewable rows), needs_validation and auto_cleared (reviewable rows; the review queue with needs_validation=true additionally lists header/coverage rows, so it can be larger by header_rows_needing_validation), per_check:{BOM_LABEL,BOM_DRAWING,LABEL_DRAWING,PCO_BOM,LABEL_REVISION}, blockers, coverage:[{kind, sku, status: OK|MISSING_BOM|MISSING_LABEL, detail, source}], groups:[{sku, family, document_ids[], warnings[]}], warnings[], parser_warnings:[{document, doc_id, warnings[]}], low_confidence_rows, state_counts:{ENGINE_RECOMMENDED, REVIEWER_1_COMPLETE, REVIEWER_2_COMPLETE, AGREED, DISAGREEMENT, FINALIZED}, terminology_version, terminology_count, relationships_used[], capabilities:{name: status}, thresholds, inputs:[{path, sha256, size_bytes, doc_type}]}`

## Results (review queue)
`GET /api/runs/{run_id}/results` params: `check` (BOM_LABEL|BOM_DRAWING|LABEL_DRAWING|PCO_BOM|LABEL_REVISION), `sku`, `classification` (EXACT|EQUIVALENT|POTENTIAL|MISMATCH|MISSING), `severity` (BLOCKER|MAJOR|MINOR|INFO), `discrepancy` (type name), `needs_validation` (true/false), `state`, `role` (item|header|reference|coverage|exempt|change), `search`, `viewer` (1|2), `blind` (true/false), `limit` (default 500), `offset`.
Default order: blocker → major → ambiguous → potential → low-confidence → sku → row id.
Returns `{total, offset, limit, rows:[{row_id, sku, check, role, engine:{classification, match_level, score, relationship_id, requires_validation, severity, discrepancies[], explanation}, decisions:{"1": Decision|null, "2": Decision|null}, state, final, effective_classification, a:{item_number, description, quantity, page, locator, file_name}|null, b:{...}|null, discrepancies:[{type, severity, detail, recommended_action}], action_items[]}]}`.
Decision: `{slot, reviewer, decision, comment, override_classification, decided_at, blind}`. In blind mode (`viewer=2&blind=true`) reviewer 1's decision is `null` until reviewer 2 has decided that row.

`GET /api/runs/{run_id}/results/{row_id}` (+ `viewer`, `blind`) → `{result: full CheckResult (source_a/source_b with evidence), evidence:{a: Evidence|null, b: Evidence|null}, decisions, state, final, effective_classification, history:[{event: engine|reviewer_1|reviewer_2|final, ...}], action_items[]}`.
Evidence: `{doc_id, doc_type, file, file_name, sha256, page, bbox:{x0,y0,x1,y1}|null, locator, raw_text, sheet, item_number, description, quantity, uom, oper_seq, category, category_reason, confidence, attributes, sub_quantity}`.

## Documents and evidence images
| GET | `/api/runs/{run_id}/documents` | `[{id, doc_type, file, file_name, sku, sha256, parser, parser_version, items, warnings[], header, pages}]` |
| GET | `/api/runs/{run_id}/documents/{doc_id}/items` | `{doc_id, doc_type, file_name, header, warnings, pages, items:[Evidence + {id, is_active}]}` (extraction verification view) |
| GET | `/api/runs/{run_id}/documents/{doc_id}/pages/{n}?highlight={row_id}&dpi=110` | `image/png` of page n (1-based); with `highlight`, the evidence box of that row on this document is outlined. Bbox coordinates in Evidence are PDF points at 72 dpi; the image is rendered at `dpi`, so scale = dpi/72. 404 for spreadsheet sources. |

## Decisions
| POST | `/api/runs/{run_id}/decisions` | `{row_id, slot:1|2, reviewer, decision: ACCEPT|OVERRIDE|CONFIRM_DISCREPANCY|NEEDS_MORE_INFORMATION, comment?, override_classification? (required for OVERRIDE), blind?}` → `{row_id, state, decisions, effective_classification}` |
| POST | `/api/runs/{run_id}/finalize` | `{row_id, final_decision, by, note?}` → `{row_id, state}` |
| POST | `/api/runs/{run_id}/bulk-accept` | `{slot, reviewer}` → `{accepted}` (only rows with no discrepancy and not needing validation) |
| POST | `/api/runs/{run_id}/relationships/from-row` | `{row_id, by, scope? (global|family:<prefix>|sku:<code>), anchor? (bind to the BOM item number), canonical?, aliases?, doc_types?, notes?}` → Relationship |

## Relationship mining
| GET | `/api/runs/{run_id}/mining?min_skus=2` | `[{a_text, b_text, a_key, b_key, pair_key, sku_count, skus[], check_types[], row_ids[], confirmed, contradicted, item_anchors[], relationship_id, evidence}]` |
| POST | `/api/runs/{run_id}/mining/approve` | `{a_key, b_key, by, scope?, anchor?, notes?}` → Relationship |
| POST | `/api/runs/{run_id}/mining/reject` | `{a_key, b_key, by, note?}` → `{rejected}` |

## Action items, verify & close, business case
| POST | `/api/runs/{run_id}/action-items` | `{row_id, reviewer, owner?}` → ActionItem |
| GET | `/api/action-items?status=&run_id=` | `[ActionItem]` |
| PATCH | `/api/action-items/{id}` | `{status? (OPEN|IN_PROGRESS|RESOLVED|CLOSED|REJECTED), owner?, by, note?}` → ActionItem |
| POST | `/api/runs/{run_id}/verify-and-close` | → `{run_id, resolved[], still_open[], not_covered[]}` |
| GET | `/api/runs/{run_id}/business-case` | params override assumptions: `baseline_minutes_per_sku, hourly_rate, skus_per_project, projects_per_year, reviewers, minutes_per_validation_row, minutes_per_cleared_row, target_reduction_pct` → `{skus, rows, auto_cleared, needs_validation, estimated_minutes_per_sku, minutes_saved_per_sku, reduction_pct, hours_saved_per_project, annual_savings, meets_target, assumptions[], per_sku, confirmable_rows, needs_validation_after_confirmation, estimated_minutes_per_sku_after_confirmation, reduction_pct_after_confirmation, hours_saved_per_project_after_confirmation, annual_savings_after_confirmation, meets_target_after_confirmation}` — the `*_after_confirmation` fields are a labelled projection (strong POTENTIAL pairings confirmed as relationships), not a measurement |

ActionItem: `{id, run_id, row_id, sku, check_type, discrepancy_type, severity, detail, recommended_action, owner, status, reviewer, created_at, updated_at, resolved_in_run, resolved_at, comparison_key}`.

## Exports
| GET | `/api/runs/{run_id}/export.xlsx` | workbook with reviewer decisions merged |
| GET | `/api/runs/{run_id}/annotated-bom/{doc_id}` | PDF; headers `X-Kaizen-Fallback` (true when the BOM had no page geometry) and `X-Kaizen-Marks` |

## Terminology
| GET | `/api/terminology?search=&scope=&all=` | `[Relationship + {usage}]` |
| POST | `/api/terminology` | `{canonical, aliases[], scope, doc_types[], item_anchors[], provenance?, by, notes}` |
| GET | `/api/terminology/{id}` · PUT `/api/terminology/{id}` `{canonical?, aliases?, scope?, doc_types?, item_anchors?, notes?, by, note}` · POST `/{id}/deactivate` `{by}` · POST `/{id}/activate` · DELETE `/{id}?by=` · GET `/{id}/history` |
| GET | `/api/terminology/export.xlsx` · POST `/api/terminology/import` (multipart `file`, form `by`) → `{summary (string, e.g. "created 1, updated 0, unchanged 9, errors 0"), created, updated, unchanged, errors[]}` |
| GET | `/api/audit?limit=200` | recent audit events |

Relationship: `{id, canonical, aliases[], scope, doc_types[], item_anchors[], provenance (manual|learned|imported), created_by, created_at, updated_at, active, notes, version}`.

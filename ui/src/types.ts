// Typed mirror of docs/api-contract.md. Field names are the API's; do not rename.

export type Classification = "EXACT" | "EQUIVALENT" | "POTENTIAL" | "MISMATCH" | "MISSING";
export const CLASSIFICATIONS: Classification[] = ["EXACT", "EQUIVALENT", "POTENTIAL", "MISMATCH", "MISSING"];

export type Severity = "BLOCKER" | "MAJOR" | "MINOR" | "INFO";
export const SEVERITIES: Severity[] = ["BLOCKER", "MAJOR", "MINOR", "INFO"];

export type CheckType = "BOM_LABEL" | "BOM_DRAWING" | "LABEL_DRAWING" | "PCO_BOM" | "LABEL_REVISION";
export const CHECK_TYPES: CheckType[] = ["BOM_LABEL", "BOM_DRAWING", "LABEL_DRAWING", "PCO_BOM", "LABEL_REVISION"];

export type DocType = "BOM" | "LABEL" | "DRAWING" | "PCO";
export const DOC_TYPES: DocType[] = ["BOM", "LABEL", "DRAWING", "PCO"];

export type ReviewState =
  | "ENGINE_RECOMMENDED"
  | "REVIEWER_1_COMPLETE"
  | "REVIEWER_2_COMPLETE"
  | "AGREED"
  | "DISAGREEMENT"
  | "FINALIZED";
export const REVIEW_STATES: ReviewState[] = [
  "ENGINE_RECOMMENDED",
  "REVIEWER_1_COMPLETE",
  "REVIEWER_2_COMPLETE",
  "AGREED",
  "DISAGREEMENT",
  "FINALIZED",
];

export type DecisionKind = "ACCEPT" | "OVERRIDE" | "CONFIRM_DISCREPANCY" | "NEEDS_MORE_INFORMATION";
export const DECISION_KINDS: DecisionKind[] = ["ACCEPT", "OVERRIDE", "CONFIRM_DISCREPANCY", "NEEDS_MORE_INFORMATION"];
export const DECISION_LABELS: Record<DecisionKind, string> = {
  ACCEPT: "Accept",
  OVERRIDE: "Override",
  CONFIRM_DISCREPANCY: "Confirm discrepancy",
  NEEDS_MORE_INFORMATION: "Needs more information",
};

export type ActionStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED" | "REJECTED";
export const ACTION_STATUSES: ActionStatus[] = ["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "REJECTED"];

export type Role = "item" | "header" | "reference" | "coverage" | "exempt" | "change";
export const ROLES: Role[] = ["item", "header", "reference", "coverage", "exempt", "change"];

export const DISCREPANCY_TYPES = [
  "QTY_MISMATCH",
  "DESC_MISMATCH",
  "MISSING_IN_LABEL",
  "MISSING_IN_BOM",
  "REF_PARENT_MISMATCH",
  "AMBIGUOUS_MATCH",
  "LOW_EXTRACTION_CONFIDENCE",
  "MISSING_IN_DRAWING",
  "EXTRA_ON_DRAWING",
  "PCO_CHANGE_NOT_APPLIED",
  "PCO_QTY_SEQ_MISMATCH",
  "BOM_MISSING_FOR_AFFECTED_CODE",
  "UNEXPECTED_LABEL_CHANGE",
  "EXPECTED_CHANGE_ABSENT",
  "DRAWING_REV_MISMATCH",
];

export interface Health {
  status: string;
  version: string;
  workspace: string;
}

export interface RunListItem {
  run_id: string;
  created_at: string;
  input_root: string;
  tool_version: string;
  terminology_version: string;
  json_path: string;
  summary: { rows: number; skus: number; documents: number; needs_validation: number } & Record<Classification, number>;
}

export interface Coverage {
  kind: string;
  sku: string;
  status: string; // OK | MISSING_BOM | MISSING_LABEL | MISSING_DRAWING | INFO
  detail: string;
  source: string;
}
export interface SkuGroup {
  sku: string;
  family: string;
  document_ids: string[];
  warnings: string[];
}
export interface ParserWarning {
  document: string;
  doc_id: string;
  warnings: string[];
}
export interface InputFile {
  path: string;
  sha256: string;
  size_bytes: number;
  doc_type: string | null;
}

export interface RunSummary {
  run_id: string;
  timestamp: string;
  input_root: string;
  tool_version: string;
  skus: number;
  documents: number;
  documents_by_type: Record<DocType, number>;
  unrecognised_files: string[];
  rows: number;
  // Added by the API after the contract was written: counts/needs_validation/auto_cleared cover reviewable
  // rows only (item + change roles); header/reference/coverage/exempt rows are listed but not counted as effort.
  reviewable_rows?: number;
  exempt_rows?: number;
  header_rows_needing_validation?: number;
  counts: Record<Classification, number>;
  needs_validation: number;
  auto_cleared: number;
  per_check: Record<CheckType, number>;
  blockers: number;
  coverage: Coverage[];
  groups: SkuGroup[];
  warnings: string[];
  parser_warnings: ParserWarning[];
  low_confidence_rows: number;
  state_counts: Record<ReviewState, number>;
  terminology_version: string;
  terminology_count: number;
  relationships_used: string[];
  capabilities: Record<string, string>;
  thresholds: Record<string, number>;
  inputs: InputFile[];
}

export interface Decision {
  slot: number;
  reviewer: string;
  decision: DecisionKind;
  comment: string;
  override_classification: Classification | null;
  decided_at: string;
  blind: boolean;
}
export interface Final {
  final_decision: DecisionKind;
  finalized_by: string;
  finalized_at: string;
  note: string;
}
export type Slot = "1" | "2";
export type DecisionsBySlot = Record<Slot, Decision | null>;

export interface SideSummary {
  item_number: string | null;
  description: string;
  quantity: string | null;
  page: number | null;
  locator: string | null;
  file_name: string;
}
export interface Discrepancy {
  type: string;
  severity: Severity;
  detail: string;
  recommended_action: string;
}
export interface EngineView {
  classification: Classification;
  match_level: string;
  score: number | null;
  relationship_id: string | null;
  requires_validation: boolean;
  severity: Severity | null;
  discrepancies: string[];
  explanation: string;
}
export interface ResultRow {
  row_id: string;
  sku: string;
  check: CheckType;
  role: Role;
  engine: EngineView;
  decisions: DecisionsBySlot;
  state: ReviewState;
  final: Final | null;
  effective_classification: Classification;
  a: SideSummary | null;
  b: SideSummary | null;
  discrepancies: Discrepancy[];
  action_items: string[];
}
export interface ResultsPage {
  total: number;
  offset: number;
  limit: number;
  rows: ResultRow[];
}
export interface ResultsQuery {
  check?: string;
  sku?: string;
  classification?: string;
  severity?: string;
  discrepancy?: string;
  needs_validation?: boolean;
  state?: string;
  role?: string;
  search?: string;
  viewer?: number;
  blind?: boolean;
  limit?: number;
  offset?: number;
}
export interface ViewerParams {
  viewer: 1 | 2;
  blind: boolean;
}

export interface BBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}
export interface SubQuantity {
  value: number;
  kind: string;
  raw: string;
}
export interface Evidence {
  doc_id: string;
  doc_type: DocType;
  file: string;
  file_name: string;
  sha256: string;
  page: number | null;
  bbox: BBox | null;
  locator: string | null;
  raw_text: string;
  sheet: string | null;
  item_number: string | null;
  description: string;
  quantity: string | null;
  uom: string | null;
  oper_seq: string | null;
  category: string;
  category_reason: string;
  confidence: number;
  attributes: Record<string, unknown>;
  sub_quantity: SubQuantity | null;
}

export interface SourceItemRef {
  id: string;
  doc_id: string;
  item_number: string | null;
  description: string;
}
export interface CheckResultFull {
  row_id: string;
  sku: string;
  check: CheckType;
  role: Role;
  source_a: SourceItemRef | null;
  source_b: SourceItemRef | null;
  normalized_a: string | null;
  normalized_b: string | null;
  classification: Classification;
  match_level: string;
  score: number | null;
  relationship_id: string | null;
  explanation: string;
  discrepancies: Discrepancy[];
  requires_validation: boolean;
}

export interface HistoryEvent {
  event: string; // engine | reviewer_1 | reviewer_2 | final
  detail?: string;
  slot?: number;
  reviewer?: string;
  decision?: DecisionKind;
  comment?: string;
  override_classification?: Classification | null;
  decided_at?: string;
  blind?: boolean;
  final_decision?: DecisionKind;
  finalized_by?: string;
  finalized_at?: string;
  note?: string;
}

export interface ActionItem {
  id: string;
  run_id: string;
  row_id: string;
  sku: string;
  check_type: string;
  discrepancy_type: string;
  severity: string;
  detail: string;
  recommended_action: string;
  owner: string;
  status: ActionStatus;
  reviewer: string;
  created_at: string;
  updated_at: string;
  resolved_in_run: string;
  resolved_at: string;
  comparison_key: string;
}

export interface RowDetail {
  result: CheckResultFull;
  evidence: { a: Evidence | null; b: Evidence | null };
  decisions: DecisionsBySlot;
  state: ReviewState;
  final: Final | null;
  effective_classification: Classification;
  history: HistoryEvent[];
  action_items: ActionItem[];
}

export interface DecisionResponse {
  row_id: string;
  state: ReviewState;
  decisions: DecisionsBySlot;
  effective_classification: Classification | null;
}

export interface DocumentSummary {
  id: string;
  doc_type: DocType;
  file: string;
  file_name: string;
  sku: string | null;
  sha256: string;
  parser: string;
  parser_version: string;
  items: number;
  warnings: string[];
  header: Record<string, unknown>;
  pages: number;
}
export interface DocumentItem extends Evidence {
  id: string;
  is_active: boolean;
}
export interface DocumentItems {
  doc_id: string;
  doc_type: DocType;
  file_name: string;
  header: Record<string, unknown>;
  warnings: string[];
  pages: number;
  items: DocumentItem[];
}

export interface Relationship {
  id: string;
  canonical: string;
  aliases: string[];
  scope: string;
  doc_types: string[];
  item_anchors: string[];
  provenance: string; // manual | learned | imported
  created_by: string;
  created_at: string;
  updated_at: string;
  active: boolean;
  notes: string;
  version: number;
  usage?: number;
}
export interface RelationshipHistory {
  version: number;
  change_type: string;
  changed_by: string;
  changed_at: string;
  change_note: string;
  payload: Relationship;
}
export interface ImportResult {
  summary: string;
  created: number;
  updated: number;
  unchanged: number;
  errors: string[];
}

export interface MiningSuggestion {
  a_text: string;
  b_text: string;
  a_key: string;
  b_key: string;
  pair_key: string;
  sku_count: number;
  skus: string[];
  check_types: string[];
  row_ids: string[];
  confirmed: number;
  contradicted: number;
  item_anchors: string[];
  relationship_id: string | null;
  evidence: string;
}

export interface VerifyOutcome {
  run_id: string;
  resolved: string[];
  still_open: string[];
  not_covered: string[];
}

export interface PerSku {
  rows: number;
  needs_validation: number;
  auto_cleared: number;
  estimated_minutes: number;
}
export interface BusinessCase {
  skus: number;
  rows: number;
  auto_cleared: number;
  needs_validation: number;
  estimated_minutes_per_sku: number;
  minutes_saved_per_sku: number;
  reduction_pct: number;
  hours_saved_per_project: number;
  annual_savings: number;
  meets_target: boolean;
  baseline_minutes_per_sku: number;
  hourly_rate: number;
  skus_per_project: number;
  projects_per_year: number;
  reviewers: number;
  assumptions: string[];
  per_sku: Record<string, PerSku>;
  // Projection (not in the contract; present in newer API builds): strong fuzzy pairings a reviewer typically
  // confirms once and saves as relationships, after which the next run auto-clears them.
  confirmable_rows?: number;
  needs_validation_after_confirmation?: number;
  estimated_minutes_per_sku_after_confirmation?: number;
  reduction_pct_after_confirmation?: number;
  hours_saved_per_project_after_confirmation?: number;
  annual_savings_after_confirmation?: number;
  meets_target_after_confirmation?: boolean;
}
export interface BusinessParams {
  baseline_minutes_per_sku?: number;
  hourly_rate?: number;
  skus_per_project?: number;
  projects_per_year?: number;
  reviewers?: number;
  minutes_per_validation_row?: number;
  minutes_per_cleared_row?: number;
  target_reduction_pct?: number;
}

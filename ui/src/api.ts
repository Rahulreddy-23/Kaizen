// Thin typed client for the local Kaizen API (docs/api-contract.md). Relative URLs only, so the same bundle
// works from the Vite dev server (proxy) and when served by the backend at "/".
import type {
  QuickView,
  Profile,
  Invitation,
  RunShare,
  ActionItem,
  ActionStatus,
  Classification,
  DecisionKind,
  DecisionResponse,
  DocumentItems,
  DocumentSummary,
  Health,
  ImportResult,
  TerminologyImportOptions,
  TerminologySource,
  MiningSuggestion,
  Relationship,
  RelationshipHistory,
  ResultsPage,
  ResultsQuery,
  Worklist,
  RunDiff,
  RoundTripResult,
  CurrentSession,
  ReviewSession,
  ReviewState,
  RowDetail,
  RunListItem,
  RunSummary,
  VerifyOutcome,
  ViewerParams,
} from "./types";
import type { Annotation, DrawingBody, GroundTruthBody, LearningReport, LearningRow, LearningSummary } from "./learning";
import { uploadProblem, type UploadFolder } from "./lib/uploads";
import { notifyDataChanged } from "./lib/dataRefresh";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface RunProgress { percent: number; stage: string }
export interface PathRunResult { runs: RunSummary[]; failures: {path: string; message: string}[] }

type Params = Record<string, string | number | boolean | null | undefined>;

function qs(params: Params): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

async function request<T>(path: string, init?: RequestInit, onProgress?: (value: RunProgress) => void): Promise<T> {
  let res: Response;
  try {
    res = await fetch(onProgress ? `${path}?stream=true` : path, { cache: "no-store", ...init });
  } catch (e) {
    throw new ApiError(0, `Cannot reach the API (${path}). Is \`kaizen serve\` running on port 8765? ${(e as Error).message}`);
  }
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body && body.detail !== undefined) {
        if (typeof body.detail === "string") msg = body.detail;
        else if (Array.isArray(body.detail)) msg = body.detail.map((issue: { loc?: (string | number)[]; msg?: string }) => `${issue.loc?.slice(1).join(".") || "Input"}: ${issue.msg || "invalid value"}`).join("; ");
        else msg = JSON.stringify(body.detail);
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, msg);
  }
  const data = onProgress ? await readRunStream<T>(res, onProgress) : res.status === 204 ? undefined as T : await res.json() as T;
  if (init?.method && !["GET", "HEAD"].includes(init.method.toUpperCase())) notifyDataChanged(path);
  return data;
}

async function readRunStream<T>(response: Response, onProgress: (value: RunProgress) => void): Promise<T> {
  if (!response.body || !response.headers.get("content-type")?.includes("application/x-ndjson")) {
    throw new ApiError(0, "The server cannot report cross-check progress. Refresh after restarting Kaizen.");
  }
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let pending = "", previous = 0;
  try {
    while (true) {
      const {value, done} = await reader.read();
      pending += decoder.decode(value, {stream: !done});
      const lines = pending.split("\n");
      pending = lines.pop()!;
      if (done && pending.trim()) lines.push(pending);
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === "error") throw new ApiError(event.status, event.detail);
        if (event.type === "result") return event.data as T;
        if (event.type === "progress" && Number.isFinite(event.percent)) {
          previous = Math.max(previous, Math.min(100, Math.max(0, Math.floor(event.percent))));
          onProgress({percent: previous, stage: event.stage});
        }
      }
      if (done) break;
    }
    throw new ApiError(0, "The connection ended before a result arrived. Refresh All runs before retrying; your run may have been saved.");
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "The progress connection was interrupted. Refresh All runs before retrying; your run may have been saved.");
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

const enc = encodeURIComponent;

export interface DecisionBody {
  expected_revision?: number;
  row_id: string;
  decision: DecisionKind;
  comment?: string;
  override_classification?: Classification;
}
export interface FinalizeBody {
  expected_revision: number;
  confirm_self_approval: boolean;
  row_id: string;
  final_decision: DecisionKind;
  note?: string;
}
export interface FromRowBody {
  row_id: string;
  scope?: string;
  anchor?: boolean;
  canonical?: string;
  aliases?: string[];
  doc_types?: string[];
  notes?: string;
}
export interface RelationshipCreateBody {
  canonical: string;
  aliases: string[];
  scope: string;
  doc_types: string[];
  item_anchors: string[];
  provenance?: string;
  by: string;
  notes: string;
}
export interface RelationshipUpdateBody {
  canonical?: string;
  aliases?: string[];
  scope?: string;
  doc_types?: string[];
  item_anchors?: string[];
  notes?: string;
  by: string;
  note: string;
}

export const api = {
  learning: {
    summary: (runId: string) => request<LearningSummary>(`/api/runs/${enc(runId)}/learning`),
    enable: (runId: string) => request<LearningSummary>(`/api/runs/${enc(runId)}/learning/enable`, {method: "POST"}),
    row: (runId: string, rowId: string) => request<LearningRow>(`/api/runs/${enc(runId)}/learning/rows/${enc(rowId)}`),
    annotate: (runId: string, rowId: string, body: GroundTruthBody) => request<Annotation>(`/api/runs/${enc(runId)}/learning/rows/${enc(rowId)}`, json("PUT", body)),
    approve: (runId: string, rowId: string, version: number, approve: boolean) => request<Annotation>(`/api/runs/${enc(runId)}/learning/rows/${enc(rowId)}/approve`, json("POST", {expected_version: version, approve})),
    drawing: (runId: string, sku: string, body: DrawingBody) => request<unknown>(`/api/runs/${enc(runId)}/learning/drawings/${enc(sku)}`, json("PUT", body)),
    approveDrawing: (runId: string, sku: string, version: number, approve: boolean) => request<unknown>(`/api/runs/${enc(runId)}/learning/drawings/${enc(sku)}/approve`, json("POST", {expected_version: version, approve})),
    shadow: (runId: string) => request<LearningReport>(`/api/runs/${enc(runId)}/learning/shadow`, {method: "POST"}),
    exportUrl: (runId: string, split: "train" | "evaluation") => `/api/runs/${enc(runId)}/learning/export.json?split=${split}`,
    observationsUrl: (runId: string) => `/api/runs/${enc(runId)}/learning/observations.json`,
  },
  health: () => request<Health>("/api/health"),

  profiles: () => request<{email: string}[]>("/api/profiles"),
  invitations: () => request<Invitation[]>("/api/admin/invitations"),
  invite: (email: string) => request<Invitation & {code: string}>("/api/admin/invitations", json("POST", {email})),
  revokeInvitation: (id: string) => request<{revoked: boolean}>(`/api/admin/invitations/${enc(id)}`, {method: "DELETE"}),
  users: () => request<Profile[]>("/api/admin/users"),
  updateUser: (email: string, body: Partial<Profile>) => request<Profile>(`/api/admin/users/${enc(email)}`, json("PATCH", body)),
  shares: (runId: string) => request<RunShare[]>(`/api/runs/${enc(runId)}/sharing`),
  share: (runId: string, email: string, permission: "view" | "edit" | null) => request<RunShare[]>(`/api/runs/${enc(runId)}/sharing`, json("PUT", {email, permission})),
  renameRun: (runId: string, name: string) => request<unknown>(`/api/runs/${enc(runId)}`, json("PATCH", {name})),
  deleteRun: (runId: string) => request<{deleted: boolean}>(`/api/runs/${enc(runId)}`, {method: "DELETE"}),
  restoreRun: (runId: string) => request<{restored: boolean}>(`/api/runs/${enc(runId)}/restore`, {method: "POST"}),
  listDeletedRuns: () => request<RunListItem[]>("/api/runs?deleted=true"),
  copyRun: (runId: string) => request<RunSummary>(`/api/runs/${enc(runId)}/copy`, {method: "POST"}),
  downloadUrl: (runId: string) => `/api/runs/${enc(runId)}/download.zip`,
  // ---- runs
  listRuns: () => request<RunListItem[]>("/api/runs"),
  loadDemo: (onProgress?: (value: RunProgress) => void) => request<RunSummary>("/api/demo/load", { method: "POST" }, onProgress),
  // One run per folder; every folder must hold exactly a BOM, a label and a drawing, as with uploads.
  runFromPath: (path: string, name = "", onProgress?: (value: RunProgress) => void) => request<PathRunResult>("/api/runs/from-path", json("POST", { path, name }), onProgress),
  uploadRun: async (folders: UploadFolder[], name = "", onProgress?: (value: RunProgress) => void) => {
    if (folders.length > 1) throw new ApiError(400, "Send one folder per run.");
    const problem = uploadProblem(folders);
    if (problem) throw new ApiError(400, problem);
    const fd = new FormData();
    fd.append("name", name);
    for (const folder of folders) for (const f of folder.files) fd.append("files", f, `${folder.name}/${f.name}`);
    return request<RunSummary>("/api/runs/upload", { method: "POST", body: fd }, onProgress);
  },
  getRun: (runId: string) => request<RunSummary>(`/api/runs/${enc(runId)}`),
  quickView: (runId: string, query: {sku?: string; view?: "components" | "text"; status?: string; search?: string; offset?: number}) =>
    request<QuickView>(`/api/runs/${enc(runId)}/quick-view${qs(query)}`),
  quickExportUrl: (runId: string, sku?: string) => `/api/runs/${enc(runId)}/quick-view/export.xlsx${qs({sku})}`,

  // ---- results / evidence
  getResults: (runId: string, q: ResultsQuery) => request<ResultsPage>(`/api/runs/${enc(runId)}/results${qs(q as Params)}`),
  // The session decides which decisions are visible; `_v` only forces a refetch when it changes.
  getRow: (runId: string, rowId: string, _v: ViewerParams) =>
    request<RowDetail>(`/api/runs/${enc(runId)}/results/${enc(rowId)}`),
  pageImageUrl: (runId: string, docId: string, page: number, highlight?: string | null, dpi = 110) =>
    `/api/runs/${enc(runId)}/documents/${enc(docId)}/pages/${page}${qs({ highlight: highlight ?? undefined, dpi })}`,

  // ---- decisions
  postDecision: (runId: string, body: DecisionBody) => request<DecisionResponse>(`/api/runs/${enc(runId)}/decisions`, json("POST", body)),
  finalize: (runId: string, body: FinalizeBody) => request<{ row_id: string; state: ReviewState }>(`/api/runs/${enc(runId)}/finalize`, json("POST", body)),
  bulkAccept: (runId: string) => request<{ accepted: number }>(`/api/runs/${enc(runId)}/bulk-accept`, json("POST", {})),

  // ---- reviewer session: identity, slot and blind mode are held by the server
  // Sign-up creates the account; sign-in exchanges the password for a session. The password is only
  // ever sent, never stored or echoed here — the session lives in an HttpOnly cookie this code cannot read.
  currentSession: () => request<CurrentSession>("/api/sessions/current"),
  signUp: (email: string, password: string, invitation: string) => request<{ ok: boolean; email: string }>("/api/auth/signup", json("POST", { email, password, invitation })),
  signIn: (email: string, password: string) => request<ReviewSession>("/api/auth/signin", json("POST", { email, password })),
  signOut: () => request<{ ended: boolean }>("/api/sessions/current", { method: "DELETE" }),
  relationshipFromRow: (runId: string, body: FromRowBody) => request<Relationship>(`/api/runs/${enc(runId)}/relationships/from-row`, json("POST", body)),

  // ---- documents
  getDocuments: (runId: string) => request<DocumentSummary[]>(`/api/runs/${enc(runId)}/documents`),
  getDocumentItems: (runId: string, docId: string) => request<DocumentItems>(`/api/runs/${enc(runId)}/documents/${enc(docId)}/items`),
  annotatedBomUrl: (runId: string, docId: string) => `/api/runs/${enc(runId)}/annotated-bom/${enc(docId)}`,

  // ---- mining
  certificateUrl: (runId: string, sku?: string) => `/api/runs/${enc(runId)}/certificate.pdf${qs({ sku })}`,
  getDiff: (runId: string, against: string) => request<RunDiff>(`/api/runs/${enc(runId)}/diff${qs({ against })}`),
  importDecisions: (runId: string, file: File, opts: { dryRun?: boolean; force?: boolean } = {}) => {
    const fd = new FormData();
    fd.append("file", file, file.name);
    fd.append("dry_run", opts.dryRun ? "true" : "false");
    fd.append("force", opts.force ? "true" : "false");
    return request<RoundTripResult>(`/api/runs/${enc(runId)}/decisions/import`, { method: "POST", body: fd });
  },
  getWorklist: (runId: string) => request<Worklist>(`/api/runs/${enc(runId)}/terminology-worklist`),
  getMining: (runId: string, minSkus = 2) => request<MiningSuggestion[]>(`/api/runs/${enc(runId)}/mining${qs({ min_skus: minSkus })}`),
  approveMining: (runId: string, body: { a_key: string; b_key: string; by: string; scope?: string; anchor?: boolean; notes?: string }) =>
    request<Relationship>(`/api/runs/${enc(runId)}/mining/approve`, json("POST", body)),
  rejectMining: (runId: string, body: { a_key: string; b_key: string; by: string; note?: string }) =>
    request<{ rejected: string }>(`/api/runs/${enc(runId)}/mining/reject`, json("POST", body)),

  // ---- action items, verify & close
  createActionItem: (runId: string, body: { row_id: string; reviewer: string; owner?: string }) =>
    request<ActionItem>(`/api/runs/${enc(runId)}/action-items`, json("POST", body)),
  listActionItems: (q: { status?: string; run_id?: string }) => request<ActionItem[]>(`/api/action-items${qs(q)}`),
  patchActionItem: (id: string, body: { status?: ActionStatus; owner?: string; by: string; note?: string }) =>
    request<ActionItem>(`/api/action-items/${enc(id)}`, json("PATCH", body)),
  verifyAndClose: (runId: string, against?: string) => request<VerifyOutcome>(`/api/runs/${enc(runId)}/verify-and-close${against ? `?against=${enc(against)}` : ""}`, { method: "POST" }),

  // ---- exports
  exportUrl: (runId: string, detail: "summary" | "complete" = "summary") => `/api/runs/${enc(runId)}/export.xlsx?detail=${detail}`,

  // ---- terminology
  terminology: {
    select: (entries: {id: string; version: number}[], selected: boolean) => request<{changed: number}>("/api/terminology/selections", json("PUT", {entries, selected})),
    list: (q: { search?: string; scope?: string; all?: boolean }) => request<Relationship[]>(`/api/terminology${qs(q)}`),
    get: (id: string) => request<Relationship>(`/api/terminology/${enc(id)}`),
    create: (body: RelationshipCreateBody) => request<Relationship>("/api/terminology", json("POST", body)),
    update: (id: string, body: RelationshipUpdateBody) => request<Relationship>(`/api/terminology/${enc(id)}`, json("PUT", body)),
    activate: (id: string, by: string) => request<Relationship>(`/api/terminology/${enc(id)}/activate`, json("POST", { by })),
    deactivate: (id: string, by: string) => request<Relationship>(`/api/terminology/${enc(id)}/deactivate`, json("POST", { by })),
    history: (id: string) => request<RelationshipHistory[]>(`/api/terminology/${enc(id)}/history`),
    exportUrl: () => "/api/terminology/export.xlsx",
    inspectFile: (file: File, sheet?: string, headerRow = 1) => {
      const fd = new FormData();
      fd.append("file", file, file.name);
      if (sheet) fd.append("sheet", sheet);
      fd.append("header_row", String(headerRow));
      return request<TerminologySource>("/api/terminology/inspect", { method: "POST", body: fd });
    },
    importFile: (file: File, by: string, options: TerminologyImportOptions = {}) => {
      const fd = new FormData();
      fd.append("file", file, file.name);
      fd.append("by", by);
      for (const [key, value] of Object.entries(options)) {
        if (value !== undefined) fd.append(key, key === "column_map" ? JSON.stringify(value) : String(value));
      }
      return request<ImportResult>("/api/terminology/import", { method: "POST", body: fd });
    },
  },
};

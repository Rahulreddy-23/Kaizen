import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ClassificationBadge, RoleTag, SeverityBadge, StateBadge } from "../components/Badges";
import { ConfirmDialog, ErrorBox, Loading, Notice } from "../components/Feedback";
import { enc, fmtQty } from "../lib/format";
import { PAGE_SIZE, queueParams, queueQueryFromParams } from "../lib/queue";
import { HotkeyHelp, HotkeyHint } from "../components/HotkeyHelp";
import { ImportDecisions } from "../components/ImportDecisions";
import { useHotkeys } from "../lib/hotkeys";
import { useReviewer } from "../lib/reviewer";
import { errorMessage, useAsync } from "../lib/useAsync";
import { CHECK_TYPES, CLASSIFICATIONS, DISCREPANCY_TYPES, REVIEW_STATES, ROLES, SEVERITIES, type ResultRow, type SideSummary } from "../types";

export default function ReviewQueuePage() {
  const { runId = "" } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const { session, viewerParams, name } = useReviewer();
  const slot: 1 | 2 = session?.slot ?? 1;
  const run = useAsync(() => api.getRun(runId), [runId]);
  const query = queueQueryFromParams(sp, viewerParams);
  const page = useAsync(() => api.getResults(runId, query), [runId, sp.toString(), viewerParams.viewer, viewerParams.blind]);

  const [search, setSearch] = useState(sp.get("q") ?? "");
  useEffect(() => setSearch(sp.get("q") ?? ""), [sp]);

  const set = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v);
    else n.delete(k);
    if (k !== "offset") n.delete("offset");
    setSp(n);
  };
  const clear = () => setSp(new URLSearchParams());
  const open = (rowId: string) => nav(`/runs/${enc(runId)}/rows/${enc(rowId)}?${queueParams(sp).toString()}`);

  // ---- keyboard: j/k highlight a row, Enter opens it, ? help
  const rows = page.data?.rows ?? [];
  const [hi, setHi] = useState<number | null>(null);
  const [help, setHelp] = useState(false);
  useEffect(() => setHi(null), [page.data]);
  useEffect(() => {
    document.querySelector('[data-selected="true"]')?.scrollIntoView({ block: "nearest" });
  }, [hi]);
  useHotkeys(
    {
      j: () => rows.length && setHi((cur) => (cur === null ? 0 : Math.min(cur + 1, rows.length - 1))),
      k: () => rows.length && setHi((cur) => (cur === null ? 0 : Math.max(cur - 1, 0))),
      Enter: () => {
        if (hi === null) return;
        const r = rows[hi];
        if (r) open(r.row_id);
      },
      "?": () => setHelp((v) => !v),
      Escape: () => setHelp(false),
    },
    [rows, hi, runId, sp.toString()],
  );

  // ---- bulk accept
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkCount, setBulkCount] = useState<number | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<string | null>(null);
  const [bulkErr, setBulkErr] = useState<string | null>(null);
  const openBulk = async () => {
    setBulkOpen(true);
    setBulkCount(null);
    setBulkErr(null);
    try {
      // Rows the API will accept: no validation needed and not yet decided by this slot.
      const other = slot === 1 ? "REVIEWER_2_COMPLETE" : "REVIEWER_1_COMPLETE";
      const [a, b] = await Promise.all([
        api.getResults(runId, { needs_validation: false, state: "ENGINE_RECOMMENDED", limit: 1 }),
        api.getResults(runId, { needs_validation: false, state: other, limit: 1 }),
      ]);
      setBulkCount(a.total + b.total);
    } catch (e) {
      setBulkErr(errorMessage(e));
    }
  };
  const doBulk = async () => {
    setBulkBusy(true);
    setBulkErr(null);
    try {
      const res = await api.bulkAccept(runId);
      setBulkMsg(`Accepted ${res.accepted} clean row${res.accepted === 1 ? "" : "s"} as ${name} (slot ${slot}). Each carries the comment "bulk accept: exact/equivalent with no discrepancy".`);
      setBulkOpen(false);
      page.reload();
      run.reload();
    } catch (e) {
      setBulkErr(errorMessage(e));
    } finally {
      setBulkBusy(false);
    }
  };

  const offset = query.offset ?? 0;
  const total = page.data?.total ?? 0;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + PAGE_SIZE, total);
  const nvOn = sp.get("nv") !== "0";

  const sel = (k: string, label: string, options: readonly string[], render?: (v: string) => string) => (
    <label className="flex items-center gap-1">
      <span className="text-gray-500">{label}</span>
      <select className="input" value={sp.get(k) ?? ""} onChange={(e) => set(k, e.target.value)}>
        <option value="">all</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {render ? render(o) : o}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <HotkeyHelp open={help} onClose={() => setHelp(false)} />
        <h1>Review queue</h1>
        <HotkeyHint />
        <span className="text-xs text-gray-500">Ordered by the engine: blockers → major → ambiguous → potential → low-confidence → SKU → row. Click a row to see the evidence and decide.</span>
        <div className="ml-auto flex gap-1">
          <button className="btn" onClick={openBulk} disabled={!name} title={name ? "" : "Enter your name in the top bar first"}>
            Accept all clean rows…
          </button>
          <ImportDecisions
            runId={runId}
            onApplied={() => {
              page.reload();
              run.reload();
            }}
          />
        </div>
      </div>

      <div className="panel p-2 flex flex-wrap gap-x-3 gap-y-2 items-center text-xs">
        {sel("sku", "SKU", (run.data?.groups ?? []).map((g) => g.sku))}
        {sel("check", "Check", CHECK_TYPES)}
        {sel("discrepancy", "Discrepancy", DISCREPANCY_TYPES)}
        {sel("severity", "Severity", SEVERITIES)}
        {sel("classification", "Classification", CLASSIFICATIONS)}
        {sel("state", "State", REVIEW_STATES, (s) => s.replace(/_/g, " "))}
        {sel("role", "Role", ROLES)}
        <label className="flex items-center gap-1" title="ON: only rows the engine could not clear. OFF: every comparison, including auto-cleared rows.">
          <input type="checkbox" checked={nvOn} onChange={(e) => set("nv", e.target.checked ? "" : "0")} />
          Needs validation only
        </label>
        <form
          className="flex items-center gap-1"
          onSubmit={(e) => {
            e.preventDefault();
            set("q", search.trim());
          }}
        >
          <input className="input w-48" placeholder="Search item, description, explanation" value={search} onChange={(e) => setSearch(e.target.value)} />
          <button className="btn" type="submit">
            Search
          </button>
        </form>
        <button className="btn" onClick={clear}>
          Clear filters
        </button>
        {viewerParams.blind && <span className="chip border-blue-700 text-blue-800">BLIND: reviewer 1 decisions hidden until you decide</span>}
      </div>

      {bulkMsg && <Notice kind="good">{bulkMsg}</Notice>}
      {page.error && <ErrorBox error={page.error} onRetry={page.reload} />}
      {page.loading && !page.data && <Loading label="Loading queue…" />}

      {page.data && (
        <div className="panel">
          <div className="panel-title">
            <span className="normal-case font-normal">
              Showing <b>{from}–{to}</b> of <b>{total}</b> comparison{total === 1 ? "" : "s"}
              {page.loading && <span className="text-gray-400"> · refreshing…</span>}
            </span>
            <span className="ml-auto flex items-center gap-1 normal-case font-normal">
              <button className="btn btn-sm" disabled={offset === 0} onClick={() => set("offset", String(Math.max(0, offset - PAGE_SIZE)))}>
                ← Prev {PAGE_SIZE}
              </button>
              <button className="btn btn-sm" disabled={to >= total} onClick={() => set("offset", String(offset + PAGE_SIZE))}>
                Next {PAGE_SIZE} →
              </button>
            </span>
          </div>
          {page.data.rows.length === 0 ? (
            <div className="p-3 text-xs text-gray-500">No rows match these filters.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Sev</th>
                    <th>SKU</th>
                    <th>Check</th>
                    <th>A — item · description · qty</th>
                    <th>B — description · qty</th>
                    <th>Engine</th>
                    <th>Discrepancies</th>
                    <th>State</th>
                    <th>Reviewer decisions</th>
                  </tr>
                </thead>
                <tbody>
                  {page.data.rows.map((row, i) => (
                    <tr key={row.row_id} className={`clickable ${hi === i ? "bg-yellow-50 outline outline-1 outline-yellow-500" : ""}`} data-selected={hi === i ? "true" : undefined} onClick={() => open(row.row_id)}>
                      <td>
                        <SeverityBadge value={row.engine.severity} />
                      </td>
                      <td className="mono whitespace-nowrap">
                        {row.sku}
                        <div className="text-2xs text-gray-400">{row.row_id}</div>
                      </td>
                      <td className="whitespace-nowrap">
                        <span className="text-2xs mono">{row.check}</span> <RoleTag value={row.role} />
                      </td>
                      <td className="min-w-[14rem]">
                        <Side s={row.a} />
                      </td>
                      <td className="min-w-[14rem]">
                        <Side s={row.b} />
                      </td>
                      <td className="whitespace-nowrap">
                        <ClassificationBadge value={row.engine.classification} title="Engine recommendation" />
                        {row.effective_classification !== row.engine.classification && (
                          <div className="text-2xs text-gray-600 mt-0.5">
                            reviewer → <ClassificationBadge value={row.effective_classification} />
                          </div>
                        )}
                        {row.engine.relationship_id && <div className="text-2xs text-gray-500 mono">{row.engine.relationship_id}</div>}
                      </td>
                      <td>
                        {row.engine.discrepancies.map((t) => (
                          <span key={t} className="chip mr-1 mb-0.5">
                            {t}
                          </span>
                        ))}
                      </td>
                      <td>
                        <StateBadge value={row.state} />
                      </td>
                      <td className="text-2xs whitespace-nowrap">
                        <Decisions row={row} blind={viewerParams.blind} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {bulkOpen && (
        <ConfirmDialog title="Accept all clean rows" confirmLabel={bulkCount ? `Accept ${bulkCount} rows` : "Accept"} onConfirm={doBulk} onCancel={() => setBulkOpen(false)} busy={bulkBusy || bulkCount === null}>
          <p>
            Records an ACCEPT decision as <b>{name}</b> (slot {slot}) on every row that has <b>no discrepancy and does not need validation</b>. Rows already decided by slot {slot} are skipped.
          </p>
          {bulkCount === null && !bulkErr && <Loading label="Counting eligible rows…" />}
          {bulkCount !== null && (
            <p className="text-sm">
              <b>{bulkCount}</b> row{bulkCount === 1 ? "" : "s"} will be accepted.
            </p>
          )}
          {bulkErr && <ErrorBox error={bulkErr} />}
          <p className="text-gray-500">
            Nothing is hidden by this: accepted rows remain in the run and the export, with the engine recommendation and your decision side by side.{" "}
            <Link className="underline" to={`/runs/${enc(runId)}/review?nv=0&classification=EXACT`}>
              Inspect clean rows first
            </Link>
            .
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}

function Side({ s }: { s: SideSummary | null }) {
  if (!s) return <span className="text-gray-400">— (no counterpart)</span>;
  return (
    <div>
      {s.item_number && <span className="mono mr-1">{s.item_number}</span>}
      <span>{s.description}</span>
      {s.quantity !== null && <span className="text-gray-600 tabular-nums"> × {fmtQty(s.quantity)}</span>}
      <div className="text-2xs text-gray-400">
        {s.file_name}
        {s.locator ? ` · ${s.locator}` : ""}
      </div>
    </div>
  );
}

function Decisions({ row, blind }: { row: ResultRow; blind: boolean }) {
  const d1 = row.decisions["1"];
  const d2 = row.decisions["2"];
  const fmt = (d: typeof d1) => (d ? `${d.decision}${d.override_classification ? `→${d.override_classification}` : ""} (${d.reviewer})` : "—");
  return (
    <div>
      <div>
        <span className="text-gray-500">R1</span> {blind && !d2 && !d1 ? <span className="text-blue-800">hidden (blind)</span> : fmt(d1)}
      </div>
      <div>
        <span className="text-gray-500">R2</span> {fmt(d2)}
      </div>
      {row.final && (
        <div>
          <span className="text-gray-500">Final</span> {row.final.final_decision} ({row.final.finalized_by})
        </div>
      )}
    </div>
  );
}

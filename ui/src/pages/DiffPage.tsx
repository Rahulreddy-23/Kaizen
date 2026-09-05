// Run-to-run diff: after corrected documents come back, show only what moved.
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ClassificationBadge } from "../components/Badges";
import { ErrorBox, Loading, Notice } from "../components/Feedback";
import { Stat } from "../components/Stat";
import { enc } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { DiffStatus, RunDiffRow } from "../types";

const STATUS_LABEL: Record<DiffStatus, string> = {
  resolved: "Resolved",
  new: "New",
  still_open: "Still open",
  changed: "Changed",
  unchanged: "Unchanged",
  gone: "Gone (not verified)",
  not_covered: "Not covered",
};
const LISTED: DiffStatus[] = ["resolved", "new", "still_open", "gone", "changed"];

export default function DiffPage() {
  const { runId = "" } = useParams();
  const [sp, setSp] = useSearchParams();
  const against = sp.get("against") ?? "";
  const runs = useAsync(() => api.listRuns(), []);
  const diff = useAsync(() => (against ? api.getDiff(runId, against) : Promise.resolve(null)), [runId, against]);
  const others = (runs.data ?? []).filter((r) => r.run_id !== runId);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <h1>Compare runs</h1>
        <label className="text-xs flex items-center gap-1">
          <span className="text-gray-500">Earlier run</span>
          <select
            className="input mono max-w-[22rem]"
            value={against}
            onChange={(e) => {
              const n = new URLSearchParams(sp);
              if (e.target.value) n.set("against", e.target.value);
              else n.delete("against");
              setSp(n);
            }}
          >
            <option value="">— choose —</option>
            {others.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id} · {r.created_at.slice(0, 16)} · {r.summary.skus} SKUs
              </option>
            ))}
          </select>
        </label>
        <span className="text-xs text-gray-500">
          → this run <span className="mono">{runId}</span>
        </span>
      </div>
      <Notice>
        Rows are matched across runs by their comparison key (check, SKU and item), not by row id. <b>Resolved</b> means the discrepancy is no longer reported; <b>gone</b> means the comparison itself
        disappeared, which is not the same as fixed. Action items close through "Verify &amp; close" on the dashboard; this page only shows the change.
      </Notice>
      {runs.error && <ErrorBox error={runs.error} onRetry={runs.reload} />}
      {!against && others.length === 0 && runs.data && <div className="panel p-3 text-xs text-gray-500">There is no other run in this workspace yet. Run the corrected documents, then compare.</div>}
      {diff.error && <ErrorBox error={diff.error} onRetry={diff.reload} />}
      {diff.loading && against && <Loading label="Comparing…" />}
      {diff.data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-2">
            {(Object.keys(STATUS_LABEL) as DiffStatus[]).map((k) => (
              <Stat key={k} label={STATUS_LABEL[k]} value={diff.data!.counts[k]} tone={k === "resolved" ? "good" : k === "new" || k === "still_open" ? "bad" : k === "gone" ? "warn" : undefined} />
            ))}
          </div>
          <div className="panel p-3 text-xs space-y-1">
            <div>
              SKUs: {diff.data.skus.common.length} in both runs
              {diff.data.skus.added.length > 0 && <> · added {diff.data.skus.added.join(", ")}</>}
              {diff.data.skus.removed.length > 0 && <> · removed {diff.data.skus.removed.join(", ")}</>}
            </div>
            <div>
              Documents changed: {diff.data.documents.changed.length === 0 ? "none" : diff.data.documents.changed.map((d) => <span key={d.path} className="mono mr-2">{d.path}</span>)}
              {diff.data.documents.added.length > 0 && <> · added {diff.data.documents.added.length}</>}
              {diff.data.documents.removed.length > 0 && <> · removed {diff.data.documents.removed.length}</>}
            </div>
          </div>
          {LISTED.map((status) => {
            const rows = diff.data!.rows.filter((r) => r.status === status);
            if (rows.length === 0) return null;
            return <DiffTable key={status} title={STATUS_LABEL[status]} rows={rows} afterRun={runId} beforeRun={against} />;
          })}
          {diff.data.rows.length === 0 && <div className="panel p-3 text-xs text-gray-500">Nothing changed between these runs.</div>}
        </>
      )}
    </div>
  );
}

function DiffTable({ title, rows, afterRun, beforeRun }: { title: string; rows: RunDiffRow[]; afterRun: string; beforeRun: string }) {
  return (
    <div className="panel">
      <div className="panel-head">
        {title} <span className="text-gray-500">({rows.length})</span>
      </div>
      <div className="overflow-x-auto">
        <table className="tbl">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Check</th>
              <th>Item</th>
              <th>Before</th>
              <th>After</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <td className="mono whitespace-nowrap">{r.sku}</td>
                <td className="mono text-2xs">{r.check}</td>
                <td className="text-xs">{(r.after ?? r.before)?.a?.[1] ?? (r.after ?? r.before)?.b?.[0] ?? r.key}</td>
                <td>
                  <Side b={r.before} run={beforeRun} />
                </td>
                <td>
                  <Side b={r.after} run={afterRun} />
                </td>
                <td className="text-2xs text-gray-600">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Side({ b, run }: { b: RunDiffRow["before"]; run: string }) {
  if (!b) return <span className="text-gray-400">—</span>;
  return (
    <span className="text-xs">
      <ClassificationBadge value={b.classification} /> {b.discrepancies.length > 0 && <span className="mono text-2xs">{b.discrepancies.join(", ")}</span>}{" "}
      <Link className="underline text-2xs" to={`/runs/${enc(run)}/rows/${enc(b.row_id)}`}>
        open
      </Link>
    </span>
  );
}

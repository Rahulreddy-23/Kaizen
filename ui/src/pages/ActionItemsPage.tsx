import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { SeverityBadge, StatusBadge } from "../components/Badges";
import { ErrorBox, Loading } from "../components/Feedback";
import { enc, fmtDate } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { errorMessage, useAsync } from "../lib/useAsync";
import { ACTION_STATUSES, type ActionItem, type ActionStatus } from "../types";

export default function ActionItemsPage() {
  const [sp, setSp] = useSearchParams();
  const status = sp.get("status") ?? "";
  const runFilter = sp.get("run_id") ?? "";
  const highlight = sp.get("id");
  const list = useAsync(() => api.listActionItems({ status: status || undefined, run_id: runFilter || undefined }), [status, runFilter]);
  const set = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v);
    else n.delete(k);
    setSp(n);
  };
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <h1>Action items</h1>
        <span className="text-xs text-gray-500">Findings created from confirmed discrepancies. “Verify & close” on a later run's dashboard resolves items whose discrepancy is gone.</span>
      </div>
      <div className="panel p-2 flex flex-wrap gap-3 items-center text-xs">
        <label className="flex items-center gap-1">
          <span className="text-gray-500">Status</span>
          <select className="input" value={status} onChange={(e) => set("status", e.target.value)}>
            <option value="">all</option>
            {ACTION_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1">
          <span className="text-gray-500">Run</span>
          <input className="input mono w-44" placeholder="run id" value={runFilter} onChange={(e) => set("run_id", e.target.value)} />
        </label>
        <span className="text-gray-500">{list.data?.length ?? 0} items</span>
      </div>
      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <Loading />}
      {list.data && (
        <div className="panel overflow-x-auto">
          <table className="tbl">
            <thead>
              <tr>
                <th>Id</th>
                <th>Status</th>
                <th>Sev</th>
                <th>SKU</th>
                <th>Check · discrepancy</th>
                <th>Detail</th>
                <th>Recommended action</th>
                <th>Owner</th>
                <th>Row</th>
                <th>Reviewer</th>
                <th>Updated</th>
                <th>Resolved</th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((a) => (
                <Row key={a.id} a={a} highlighted={a.id === highlight} onChanged={(n) => list.setData(list.data!.map((x) => (x.id === n.id ? n : x)))} />
              ))}
              {list.data.length === 0 && (
                <tr>
                  <td colSpan={12} className="text-gray-500">
                    No action items. Create one from a row's evidence view.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Row({ a, highlighted, onChanged }: { a: ActionItem; highlighted: boolean; onChanged: (a: ActionItem) => void }) {
  const { name } = useReviewer();
  const [owner, setOwner] = useState(a.owner);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const patch = async (body: { status?: ActionStatus; owner?: string }) => {
    setBusy(true);
    setErr(null);
    try {
      onChanged(await api.patchActionItem(a.id, { ...body, by: name || "reviewer" }));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <tr className={highlighted ? "selected" : ""}>
      <td className="mono whitespace-nowrap">{a.id}</td>
      <td>
        <select className="input" value={a.status} disabled={busy} onChange={(e) => patch({ status: e.target.value as ActionStatus })}>
          {ACTION_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <div className="mt-0.5">
          <StatusBadge value={a.status} />
        </div>
        {err && <div className="text-red-800 text-2xs">{err}</div>}
      </td>
      <td>
        <SeverityBadge value={a.severity} />
      </td>
      <td className="mono">{a.sku}</td>
      <td className="mono text-2xs">
        {a.check_type}
        <br />
        {a.discrepancy_type}
      </td>
      <td className="min-w-[14rem]">{a.detail}</td>
      <td className="min-w-[12rem] text-gray-700">{a.recommended_action || "—"}</td>
      <td>
        <div className="flex gap-1">
          <input className="input w-28" value={owner} disabled={busy} onChange={(e) => setOwner(e.target.value)} placeholder="owner" />
          <button className="btn btn-sm" disabled={busy || owner === a.owner} onClick={() => patch({ owner })}>
            Save
          </button>
        </div>
      </td>
      <td className="whitespace-nowrap">
        <Link className="mono underline" to={`/runs/${enc(a.run_id)}/rows/${enc(a.row_id)}?nv=0`}>
          {a.row_id}
        </Link>
        <div className="text-2xs text-gray-400 mono">{a.run_id}</div>
      </td>
      <td>{a.reviewer}</td>
      <td className="whitespace-nowrap">{fmtDate(a.updated_at)}</td>
      <td className="whitespace-nowrap">
        {a.resolved_in_run ? (
          <>
            <span className="text-green-800">in </span>
            <Link className="mono underline" to={`/runs/${enc(a.resolved_in_run)}`}>
              {a.resolved_in_run}
            </Link>
            <div className="text-2xs text-gray-500">{fmtDate(a.resolved_at)}</div>
          </>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
    </tr>
  );
}

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, Loading, Notice } from "../components/Feedback";
import { enc, familyOf } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { errorMessage, useAsync } from "../lib/useAsync";
import type { MiningSuggestion, Relationship } from "../types";

export default function MiningPage() {
  const { runId = "" } = useParams();
  const [minSkus, setMinSkus] = useState(2);
  const list = useAsync(() => api.getMining(runId, minSkus), [runId, minSkus]);
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <h1>Relationship mining suggestions</h1>
        <label className="text-xs flex items-center gap-1 ml-auto">
          <span className="text-gray-500">Seen in at least</span>
          <input type="number" min={1} className="input w-14" value={minSkus} onChange={(e) => setMinSkus(Math.max(1, Number(e.target.value) || 1))} />
          <span className="text-gray-500">SKU(s)</span>
        </label>
      </div>
      <Notice>
        Suggestions are pairs the engine matched only by fuzzy similarity, repeated across SKUs in this run. <b>Human approval required; nothing is created automatically.</b> Approving creates
        a versioned relationship (provenance “learned”) that the next run applies; rejecting records the pair so it is not suggested again.
      </Notice>
      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <Loading />}
      {list.data && list.data.length === 0 && <div className="panel p-3 text-xs text-gray-500">No suggestions at this threshold. Every repeated pairing is already covered by a relationship, or was rejected.</div>}
      {list.data && list.data.map((s) => <SuggestionCard key={s.pair_key} runId={runId} s={s} onDone={list.reload} />)}
    </div>
  );
}

function SuggestionCard({ runId, s, onDone }: { runId: string; s: MiningSuggestion; onDone: () => void }) {
  const { name } = useReviewer();
  const families = [...new Set(s.skus.map(familyOf))];
  const [scope, setScope] = useState("global");
  const [anchor, setAnchor] = useState(s.item_anchors.length > 0);
  const [notes, setNotes] = useState("");
  const [rejectNote, setRejectNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [created, setCreated] = useState<Relationship | null>(null);
  const [rejected, setRejected] = useState(false);

  const approve = async () => {
    setBusy("approve");
    setErr(null);
    try {
      setCreated(await api.approveMining(runId, { a_key: s.a_key, b_key: s.b_key, by: name, scope, anchor, notes: notes.trim() || undefined }));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  const reject = async () => {
    setBusy("reject");
    setErr(null);
    try {
      await api.rejectMining(runId, { a_key: s.a_key, b_key: s.b_key, by: name, note: rejectNote.trim() || undefined });
      setRejected(true);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  const contradicted = s.contradicted > 0;
  return (
    <div className={`panel ${rejected ? "opacity-60" : ""}`}>
      <div className="p-3 grid gap-3 lg:grid-cols-[1fr_22rem]">
        <div className="text-xs space-y-1 min-w-0">
          <div className="text-sm">
            <span className="font-semibold">{s.a_text}</span> <span className="text-gray-500">=</span> <span className="font-semibold">{s.b_text}</span>
          </div>
          <div className="text-gray-700">{s.evidence}</div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-gray-600">
            <span>
              <b className="text-gray-900">{s.sku_count}</b> SKU{s.sku_count === 1 ? "" : "s"}: <span className="mono">{s.skus.join(", ")}</span>
            </span>
            <span>
              checks: <span className="mono">{s.check_types.join(", ")}</span>
            </span>
            <span className={s.confirmed ? "text-green-800" : ""}>confirmed {s.confirmed}</span>
            <span className={contradicted ? "text-red-800 font-semibold" : ""}>contradicted {s.contradicted}</span>
            {s.item_anchors.length > 0 && (
              <span>
                BOM item numbers: <span className="mono">{s.item_anchors.join(", ")}</span>
              </span>
            )}
          </div>
          <div className="text-gray-500">
            Rows:{" "}
            {s.row_ids.slice(0, 8).map((id) => (
              <Link key={id} className="mono underline mr-1" to={`/runs/${enc(runId)}/rows/${enc(id)}?nv=0`}>
                {id}
              </Link>
            ))}
            {s.row_ids.length > 8 && `+${s.row_ids.length - 8} more`}
          </div>
          {s.relationship_id && <div className="text-green-800">Already covered by {s.relationship_id}.</div>}
        </div>
        <div className="text-xs space-y-2">
          {created ? (
            <Notice kind="good">
              Approved as{" "}
              <Link className="mono underline" to={`/terminology?id=${enc(created.id)}`}>
                {created.id}
              </Link>{" "}
              (scope <span className="mono">{created.scope}</span>). The next run will use it.
            </Notice>
          ) : rejected ? (
            <Notice>Rejected. This pair will not be suggested again.</Notice>
          ) : (
            <>
              <div className="flex flex-wrap gap-2 items-center">
                <select className="input" value={scope} onChange={(e) => setScope(e.target.value)}>
                  <option value="global">global</option>
                  {families.map((f) => (
                    <option key={f} value={`family:${f}`}>
                      family:{f}
                    </option>
                  ))}
                  {s.skus.map((k) => (
                    <option key={k} value={`sku:${k}`}>
                      sku:{k}
                    </option>
                  ))}
                </select>
                <label className={`flex items-center gap-1 ${s.item_anchors.length ? "" : "opacity-50"}`}>
                  <input type="checkbox" checked={anchor} disabled={!s.item_anchors.length} onChange={(e) => setAnchor(e.target.checked)} /> anchor to item number
                </label>
              </div>
              <input className="input w-full" placeholder="Notes (why approve)" value={notes} onChange={(e) => setNotes(e.target.value)} />
              <div className="flex gap-2">
                <button className="btn btn-primary" disabled={busy !== null || !name} onClick={approve}>
                  {busy === "approve" ? "Approving…" : "Approve"}
                </button>
              </div>
              <div className="flex gap-1 items-center border-t border-gray-200 pt-2">
                <input className="input flex-1" placeholder="Reject note" value={rejectNote} onChange={(e) => setRejectNote(e.target.value)} />
                <button className="btn btn-danger" disabled={busy !== null || !name} onClick={reject}>
                  {busy === "reject" ? "Rejecting…" : "Reject"}
                </button>
              </div>
              {!name && <div className="text-red-800">Enter your name in the top bar to approve or reject.</div>}
            </>
          )}
          {err && <ErrorBox error={err} />}
          {(created || rejected) && (
            <button className="btn btn-sm" onClick={onDone}>
              Refresh list
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, Loading, Notice } from "../components/Feedback";
import { enc, familyOf } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { errorMessage, useAsync } from "../lib/useAsync";
import type { MiningSuggestion, Relationship, Worklist } from "../types";

export default function MiningPage() {
  const { runId = "" } = useParams();
  const [minSkus, setMinSkus] = useState(2);
  const list = useAsync(() => api.getMining(runId, minSkus), [runId, minSkus]);
  const worklist = useAsync(() => api.getWorklist(runId), [runId]);
  const reloadAll = () => {
    list.reload();
    worklist.reload();
  };
  return (
    <div className="space-y-3">
      {worklist.data && <WorklistSection runId={runId} wl={worklist.data} onDone={reloadAll} />}
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
      {list.data && list.data.map((s) => <SuggestionCard key={s.pair_key} runId={runId} s={s} onDone={reloadAll} />)}
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

/** The business-case projection as a to-do list: approve these, in this order, and this many rows clear. */
function WorklistSection({ runId, wl, onDone }: { runId: string; wl: Worklist; onDone: () => void }) {
  const { name } = useReviewer();
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const items = showAll ? wl.items : wl.items.slice(0, 10);
  const approve = async (it: Worklist["items"][number]) => {
    setBusy(it.pair_key);
    setErr(null);
    try {
      await api.approveMining(runId, { a_key: it.a_key, b_key: it.b_key, by: name, scope: "global", anchor: it.item_anchors.length > 0, notes: "Approved from the terminology worklist" });
      onDone();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <section className="panel p-3 space-y-2">
      <div className="flex items-baseline gap-3 flex-wrap">
        <h1>Terminology worklist</h1>
        <span className="text-xs text-gray-600">
          {wl.needs_validation} rows need validation in this run; {wl.potential_rows} of them sit behind {wl.items.length} unconfirmed wording pairings.
        </span>
      </div>
      {wl.items.length > 0 ? (
        <p className="text-sm">
          Approving the <b>top {wl.top5.n}</b> pairings auto-clears <b className="tabular-nums">{wl.top5.rows}</b> rows ({wl.top5.pct}% of what needs validation); the top {wl.top10.n} clears{" "}
          <b className="tabular-nums">{wl.top10.rows}</b> ({wl.top10.pct}%). Each approval creates a versioned relationship that the <i>next</i> run applies. Rows marked "still review" carry a
          discrepancy or an ambiguity and stay with a reviewer regardless.
        </p>
      ) : (
        <p className="text-sm text-gray-600">Every fuzzy pairing in this run is already covered by a relationship. Nothing to approve.</p>
      )}
      {err && <ErrorBox error={err} />}
      {wl.items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="table text-xs">
            <thead>
              <tr>
                <th>#</th>
                <th>BOM wording</th>
                <th>Label / drawing wording</th>
                <th className="text-right">SKUs</th>
                <th className="text-right">Would clear</th>
                <th className="text-right">Still review</th>
                <th className="text-right">Cumulative</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={it.pair_key}>
                  <td className="tabular-nums text-gray-500">{i + 1}</td>
                  <td className="mono">{it.a_text}</td>
                  <td className="mono">{it.b_text}</td>
                  <td className="text-right tabular-nums">{it.sku_count}</td>
                  <td className="text-right tabular-nums font-semibold">{it.would_clear}</td>
                  <td className="text-right tabular-nums">{it.still_review || ""}</td>
                  <td className="text-right tabular-nums">
                    {it.cumulative_clear} <span className="text-gray-500">({it.cumulative_pct}%)</span>
                  </td>
                  <td className="whitespace-nowrap">
                    <Link className="underline mr-2" to={`/runs/${enc(runId)}/rows/${enc(it.row_ids[0])}`} title="Open the first row with its evidence">
                      evidence
                    </Link>
                    <button className="btn btn-primary" disabled={busy !== null || !name} onClick={() => approve(it)} title="Creates a global relationship (versioned, attributed to you)">
                      {busy === it.pair_key ? "Approving…" : "Approve"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {wl.items.length > 10 && (
        <button className="btn" onClick={() => setShowAll((v) => !v)}>
          {showAll ? "Show top 10" : `Show all ${wl.items.length}`}
        </button>
      )}
    </section>
  );
}

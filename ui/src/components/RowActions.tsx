import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { enc, familyOf } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { errorMessage } from "../lib/useAsync";
import type { Relationship, RowDetail } from "../types";
import { StatusBadge } from "./Badges";
import { ErrorBox, Notice } from "./Feedback";

/** "Save as relationship": turns a reviewer's judgement about this pair into an explicit, versioned rule. */
export function SaveRelationshipPanel({ runId, detail, onCreated }: { runId: string; detail: RowDetail; onCreated: () => void }) {
  const { name } = useReviewer();
  const a = detail.evidence.a;
  const b = detail.evidence.b;
  const rowId = detail.result.row_id;
  const sku = detail.result.sku;
  const [open, setOpen] = useState(false);
  const [canonical, setCanonical] = useState(b?.description ?? "");
  const [alias, setAlias] = useState(a?.description ?? "");
  const [scope, setScope] = useState("global");
  const [anchor, setAnchor] = useState(Boolean(a?.item_number));
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [created, setCreated] = useState<Relationship | null>(null);

  useEffect(() => {
    setCanonical(b?.description ?? "");
    setAlias(a?.description ?? "");
    setAnchor(Boolean(a?.item_number));
    setScope("global");
    setNotes("");
    setCreated(null);
    setErr(null);
    setOpen(false);
  }, [rowId, a?.description, b?.description, a?.item_number]);

  const existing = detail.result.relationship_id;
  if (!a || !b) {
    return existing ? (
      <div className="panel">
        <div className="panel-title">Terminology</div>
        <div className="p-3 text-xs">
          This comparison used relationship{" "}
          <Link className="mono underline" to={`/terminology?id=${enc(existing)}`}>
            {existing}
          </Link>
          .
        </div>
      </div>
    ) : null;
  }

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      const rel = await api.relationshipFromRow(runId, {
        row_id: rowId,
        scope,
        anchor,
        canonical: canonical.trim(),
        aliases: [alias.trim()],
        notes: notes.trim() || undefined,
      });
      setCreated(rel);
      onCreated();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-title">Terminology</div>
      <div className="p-3 text-xs space-y-2">
        {existing && (
          <div>
            This comparison used relationship{" "}
            <Link className="mono underline" to={`/terminology?id=${enc(existing)}`}>
              {existing}
            </Link>
            .
          </div>
        )}
        {created ? (
          <Notice kind="good">
            Created relationship{" "}
            <Link className="mono underline" to={`/terminology?id=${enc(created.id)}`}>
              {created.id}
            </Link>{" "}
            (version {created.version}, scope <span className="mono">{created.scope}</span>
            {created.item_anchors.length > 0 && (
              <>
                , anchored to <span className="mono">{created.item_anchors.join(", ")}</span>
              </>
            )}
            ). The next run will use it automatically. This run's rows are unchanged so the audit trail stays intact.
          </Notice>
        ) : !open ? (
          <div>
            <button className="btn" onClick={() => setOpen(true)}>
              Save as relationship…
            </button>
            <div className="text-2xs text-gray-500 mt-1">Record that “{a.description}” and “{b.description}” mean the same thing, as an explicit rule the engine will apply next time.</div>
          </div>
        ) : (
          <div className="space-y-2">
            <label className="block">
              <span className="label">Canonical (label wording)</span>
              <input className="input w-full" value={canonical} onChange={(e) => setCanonical(e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Alias (BOM wording)</span>
              <input className="input w-full" value={alias} onChange={(e) => setAlias(e.target.value)} />
            </label>
            <label className="block">
              <span className="label">Scope</span>
              <select className="input w-full" value={scope} onChange={(e) => setScope(e.target.value)}>
                <option value="global">global — every SKU</option>
                <option value={`family:${familyOf(sku)}`}>family:{familyOf(sku)} — this product family</option>
                <option value={`sku:${sku}`}>sku:{sku} — this SKU only</option>
              </select>
            </label>
            <label className={`flex items-center gap-2 ${a.item_number ? "" : "opacity-50"}`}>
              <input type="checkbox" checked={anchor} disabled={!a.item_number} onChange={(e) => setAnchor(e.target.checked)} />
              Bind to BOM item number <span className="mono">{a.item_number ?? "(none on this row)"}</span>
            </label>
            <label className="block">
              <span className="label">Notes (why)</span>
              <textarea className="input w-full" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={`Defaults to: saved from run ${runId} row ${rowId}`} />
            </label>
            {!name && <div className="text-red-800">Enter your name in the top bar first: relationships record who created them.</div>}
            <div className="flex gap-2">
              <button className="btn btn-primary" disabled={busy || !name || !canonical.trim() || !alias.trim()} onClick={submit}>
                {busy ? "Saving…" : "Save relationship"}
              </button>
              <button className="btn" onClick={() => setOpen(false)} disabled={busy}>
                Cancel
              </button>
            </div>
            {err && <ErrorBox error={err} />}
          </div>
        )}
      </div>
    </div>
  );
}

export function ActionItemPanel({ runId, detail, onCreated }: { runId: string; detail: RowDetail; onCreated: () => void }) {
  const { name } = useReviewer();
  const [owner, setOwner] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [okId, setOkId] = useState<string | null>(null);
  const rowId = detail.result.row_id;
  useEffect(() => {
    setErr(null);
    setOkId(null);
    setOwner("");
  }, [rowId]);
  const create = async () => {
    setBusy(true);
    setErr(null);
    try {
      const ai = await api.createActionItem(runId, { row_id: rowId, reviewer: name, owner: owner.trim() || undefined });
      setOkId(ai.id);
      onCreated();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const hasDisc = detail.result.discrepancies.length > 0;
  return (
    <div className="panel">
      <div className="panel-title">Action items</div>
      <div className="p-3 text-xs space-y-2">
        {detail.action_items.length > 0 ? (
          <ul className="space-y-1">
            {detail.action_items.map((ai) => (
              <li key={ai.id} className="flex items-center gap-2">
                <Link className="mono underline" to={`/action-items?id=${enc(ai.id)}`}>
                  {ai.id}
                </Link>
                <StatusBadge value={ai.status} />
                <span className="text-gray-600">{ai.discrepancy_type} · owner {ai.owner || "—"}</span>
                {ai.resolved_in_run && <span className="text-green-800">resolved in {ai.resolved_in_run}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-gray-500">None for this row.</div>
        )}
        {okId && <Notice kind="good">Created action item <span className="mono">{okId}</span>.</Notice>}
        <div className="flex gap-1 items-center">
          <input className="input flex-1" placeholder="Owner (optional)" value={owner} onChange={(e) => setOwner(e.target.value)} />
          <button className="btn" disabled={busy || !name || !hasDisc} onClick={create} title={hasDisc ? "" : "This row has no discrepancy to track"}>
            {busy ? "Creating…" : "Create action item"}
          </button>
        </div>
        <div className="text-2xs text-gray-500">Tracks this discrepancy as a finding. After the fix, re-run the folder and use “Verify & close” on the dashboard: items whose comparison no longer shows the discrepancy are resolved automatically.</div>
        {err && <ErrorBox error={err} />}
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type RelationshipCreateBody } from "../api";
import { ErrorBox, Loading, Notice } from "../components/Feedback";
import { fmtDate } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { errorMessage, useAsync } from "../lib/useAsync";
import { DOC_TYPES, type ImportResult, type Relationship } from "../types";

type ScopeFilter = "" | "global" | "family" | "sku";

const lines = (s: string) =>
  s
    .split(/\r?\n|,/)
    .map((x) => x.trim())
    .filter(Boolean);

export default function TerminologyPage() {
  const [sp, setSp] = useSearchParams();
  const { name } = useReviewer();
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState("");
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>("");
  const [showInactive, setShowInactive] = useState(true);
  const list = useAsync(() => api.terminology.list({ search: applied || undefined, all: true }), [applied]);
  const selectedId = sp.get("id");
  const [creating, setCreating] = useState(false);
  const [importMsg, setImportMsg] = useState<ImportResult | null>(null);
  const [importErr, setImportErr] = useState<string | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);

  const rows = useMemo(() => {
    let r = list.data ?? [];
    if (!showInactive) r = r.filter((x) => x.active);
    if (scopeFilter === "global") r = r.filter((x) => x.scope === "global");
    else if (scopeFilter) r = r.filter((x) => x.scope.startsWith(`${scopeFilter}:`));
    return r;
  }, [list.data, showInactive, scopeFilter]);

  const openRel = (id: string | null) => {
    const n = new URLSearchParams(sp);
    if (id) n.set("id", id);
    else n.delete("id");
    setSp(n, { replace: true });
  };

  const doImport = async () => {
    if (!importFile) return;
    setImporting(true);
    setImportErr(null);
    setImportMsg(null);
    try {
      setImportMsg(await api.terminology.importFile(importFile, name || "import"));
      list.reload();
    } catch (e) {
      setImportErr(errorMessage(e));
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <h1>Terminology relationships</h1>
        <div className="ml-auto flex gap-1">
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            New relationship
          </button>
          <a className="btn" href={api.terminology.exportUrl()} download>
            Export .xlsx
          </a>
        </div>
      </div>
      <Notice>
        Relationships are explicit, versioned rules maintained by reviewers, not model weights. Every run records the exact versions it used (the terminology version on the dashboard), so a
        classification can always be traced to the rule that produced it. Changing a rule never rewrites past runs.
      </Notice>

      <div className="panel p-2 flex flex-wrap gap-x-3 gap-y-2 items-center text-xs">
        <form
          className="flex items-center gap-1"
          onSubmit={(e) => {
            e.preventDefault();
            setApplied(search.trim());
          }}
        >
          <input className="input w-56" placeholder="Search canonical, aliases, notes" value={search} onChange={(e) => setSearch(e.target.value)} />
          <button className="btn" type="submit">
            Search
          </button>
        </form>
        <label className="flex items-center gap-1">
          <span className="text-gray-500">Scope</span>
          <select className="input" value={scopeFilter} onChange={(e) => setScopeFilter(e.target.value as ScopeFilter)}>
            <option value="">all</option>
            <option value="global">global</option>
            <option value="family">family:*</option>
            <option value="sku">sku:*</option>
          </select>
        </label>
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} /> Show inactive
        </label>
        <span className="text-gray-500">
          {rows.length} of {list.data?.length ?? 0}
        </span>
        <span className="ml-auto flex items-center gap-1">
          <span className="text-gray-500">Import (.xlsx or .csv)</span>
          <input type="file" accept=".xlsx,.csv" className="text-xs" onChange={(e) => setImportFile(e.target.files?.[0] ?? null)} />
          <button className="btn" disabled={!importFile || importing} onClick={doImport}>
            {importing ? "Importing…" : "Import"}
          </button>
        </span>
      </div>
      {importErr && <ErrorBox error={importErr} />}
      {importMsg && (
        <Notice kind={importMsg.errors.length ? "warn" : "good"}>
          {importMsg.summary} — created {importMsg.created}, updated {importMsg.updated}, unchanged {importMsg.unchanged}
          {importMsg.errors.length > 0 && (
            <ul className="list-disc pl-4 mt-1">
              {importMsg.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </Notice>
      )}

      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      {list.loading && !list.data && <Loading />}
      {list.data && (
        <div className="panel overflow-x-auto">
          <table className="tbl">
            <thead>
              <tr>
                <th>Id</th>
                <th>Canonical</th>
                <th>Aliases</th>
                <th>Scope</th>
                <th>Item anchors</th>
                <th>Doc types</th>
                <th>Provenance</th>
                <th>Created</th>
                <th className="text-right">Ver.</th>
                <th>Active</th>
                <th className="text-right">Usage</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className={`clickable ${r.id === selectedId ? "selected" : ""} ${r.active ? "" : "text-gray-400"}`} onClick={() => openRel(r.id)}>
                  <td className="mono whitespace-nowrap">{r.id}</td>
                  <td className="font-medium">{r.canonical}</td>
                  <td>
                    {r.aliases.map((a) => (
                      <span key={a} className="chip mr-1 mb-0.5">
                        {a}
                      </span>
                    ))}
                  </td>
                  <td className="mono">{r.scope}</td>
                  <td className="mono">{r.item_anchors.join(", ") || <span className="text-gray-400">—</span>}</td>
                  <td>{r.doc_types.join(", ") || <span className="text-gray-400">all</span>}</td>
                  <td>{r.provenance}</td>
                  <td className="whitespace-nowrap">
                    {r.created_by} · {fmtDate(r.created_at)}
                  </td>
                  <td className="text-right tabular-nums">{r.version}</td>
                  <td>{r.active ? "active" : <span className="text-red-800">inactive</span>}</td>
                  <td className="text-right tabular-nums whitespace-nowrap">used by {r.usage ?? 0} comparison{r.usage === 1 ? "" : "s"}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={11} className="text-gray-500">
                    No relationships match.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {selectedId && (
        <Drawer
          id={selectedId}
          onClose={() => openRel(null)}
          onChanged={() => {
            list.reload();
          }}
        />
      )}
      {creating && (
        <CreateForm
          onClose={() => setCreating(false)}
          onCreated={(rel) => {
            setCreating(false);
            list.reload();
            openRel(rel.id);
          }}
        />
      )}
    </div>
  );
}

function Drawer({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const { name } = useReviewer();
  const rel = useAsync(() => api.terminology.get(id), [id]);
  const hist = useAsync(() => api.terminology.history(id), [id]);
  const [form, setForm] = useState({ canonical: "", aliases: "", scope: "global", anchors: "", doc_types: [] as string[], notes: "", note: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  useEffect(() => {
    if (!rel.data) return;
    setForm({ canonical: rel.data.canonical, aliases: rel.data.aliases.join("\n"), scope: rel.data.scope, anchors: rel.data.item_anchors.join(", "), doc_types: rel.data.doc_types, notes: rel.data.notes, note: "" });
    setErr(null);
    setOk(null);
  }, [rel.data]);

  const act = async (fn: () => Promise<Relationship>, msg: string) => {
    setBusy(true);
    setErr(null);
    setOk(null);
    try {
      const r = await fn();
      rel.setData(r);
      hist.reload();
      onChanged();
      setOk(msg);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const save = () =>
    act(
      () => api.terminology.update(id, { canonical: form.canonical.trim(), aliases: lines(form.aliases), scope: form.scope.trim(), item_anchors: lines(form.anchors), doc_types: form.doc_types, notes: form.notes, by: name, note: form.note.trim() || "edited in UI" }),
      "Saved as a new version.",
    );

  const r = rel.data;
  return (
    <div className="fixed inset-y-0 right-0 z-30 w-[34rem] max-w-[95vw] bg-white border-l border-gray-400 shadow-xl overflow-y-auto">
      <div className="panel-title sticky top-0 bg-white z-10">
        <span className="mono normal-case text-sm text-gray-900">{id}</span>
        {r && (r.active ? <span className="chip border-green-700 text-green-800">active</span> : <span className="chip border-red-700 text-red-800">inactive</span>)}
        {r && <span className="normal-case font-normal text-gray-500">version {r.version}</span>}
        <button className="btn btn-sm ml-auto" onClick={onClose}>
          Close
        </button>
      </div>
      {rel.error && (
        <div className="p-3">
          <ErrorBox error={rel.error} onRetry={rel.reload} />
        </div>
      )}
      {!r && !rel.error && <Loading />}
      {r && (
        <div className="p-3 space-y-4 text-xs">
          <div className="border border-gray-300 bg-gray-50 p-2">
            <div className="label mb-1">Why it exists</div>
            <p className={r.notes ? "" : "text-gray-400"}>{r.notes || "No notes recorded."}</p>
            <dl className="kv mt-2">
              <dt>Provenance</dt>
              <dd>{r.provenance}</dd>
              <dt>Created</dt>
              <dd>
                {r.created_by} · {fmtDate(r.created_at)}
              </dd>
              <dt>Updated</dt>
              <dd>{fmtDate(r.updated_at)}</dd>
              <dt>Usage</dt>
              <dd>used by {r.usage ?? 0} comparison{r.usage === 1 ? "" : "s"} across recorded runs</dd>
            </dl>
          </div>

          <div className="space-y-2">
            <div className="label">Edit (creates a new version)</div>
            <label className="block">
              <span className="text-gray-500">Canonical</span>
              <input className="input w-full" value={form.canonical} onChange={(e) => setForm({ ...form, canonical: e.target.value })} />
            </label>
            <label className="block">
              <span className="text-gray-500">Aliases (one per line)</span>
              <textarea className="input w-full mono" rows={3} value={form.aliases} onChange={(e) => setForm({ ...form, aliases: e.target.value })} />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="block">
                <span className="text-gray-500">Scope (global · family:&lt;prefix&gt; · sku:&lt;code&gt;)</span>
                <input className="input w-full mono" value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })} />
              </label>
              <label className="block">
                <span className="text-gray-500">Item anchors (BOM item numbers, comma-separated)</span>
                <input className="input w-full mono" value={form.anchors} onChange={(e) => setForm({ ...form, anchors: e.target.value })} />
              </label>
            </div>
            <div>
              <span className="text-gray-500">Document types (none = all)</span>
              <div className="flex gap-3 mt-0.5">
                {DOC_TYPES.map((t) => (
                  <label key={t} className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={form.doc_types.includes(t)}
                      onChange={(e) => setForm({ ...form, doc_types: e.target.checked ? [...form.doc_types, t] : form.doc_types.filter((x) => x !== t) })}
                    />
                    {t}
                  </label>
                ))}
              </div>
            </div>
            <label className="block">
              <span className="text-gray-500">Notes</span>
              <textarea className="input w-full" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </label>
            <label className="block">
              <span className="text-gray-500">Change note (why this edit)</span>
              <input className="input w-full" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </label>
            {!name && <div className="text-red-800">Enter your name in the top bar: every change records who made it.</div>}
            <div className="flex gap-2 flex-wrap">
              <button className="btn btn-primary" disabled={busy || !name || !form.canonical.trim()} onClick={save}>
                {busy ? "Saving…" : "Save new version"}
              </button>
              {r.active ? (
                <button className="btn btn-danger" disabled={busy || !name} onClick={() => act(() => api.terminology.deactivate(id, name), "Deactivated. Future runs will not use it; past runs are unchanged.")}>
                  Deactivate
                </button>
              ) : (
                <button className="btn" disabled={busy || !name} onClick={() => act(() => api.terminology.activate(id, name), "Activated.")}>
                  Activate
                </button>
              )}
            </div>
            {err && <ErrorBox error={err} />}
            {ok && <Notice kind="good">{ok}</Notice>}
          </div>

          <div>
            <div className="label mb-1">History</div>
            {hist.error && <ErrorBox error={hist.error} onRetry={hist.reload} />}
            {hist.data && (
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Ver.</th>
                    <th>Change</th>
                    <th>By</th>
                    <th>When</th>
                    <th>Snapshot</th>
                  </tr>
                </thead>
                <tbody>
                  {[...hist.data].reverse().map((h) => (
                    <tr key={h.version}>
                      <td className="tabular-nums">{h.version}</td>
                      <td>
                        {h.change_type}
                        {h.change_note && <div className="text-gray-600">“{h.change_note}”</div>}
                      </td>
                      <td>{h.changed_by}</td>
                      <td className="whitespace-nowrap">{fmtDate(h.changed_at)}</td>
                      <td className="text-gray-700">
                        <b>{h.payload.canonical}</b> = {h.payload.aliases.join(" | ")}
                        <div className="text-2xs text-gray-500 mono">
                          {h.payload.scope}
                          {h.payload.item_anchors.length ? ` · anchors ${h.payload.item_anchors.join(", ")}` : ""}
                          {h.payload.active ? "" : " · inactive"}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CreateForm({ onClose, onCreated }: { onClose: () => void; onCreated: (r: Relationship) => void }) {
  const { name } = useReviewer();
  const [form, setForm] = useState({ canonical: "", aliases: "", scope: "global", anchors: "", doc_types: [] as string[], notes: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      const body: RelationshipCreateBody = {
        canonical: form.canonical.trim(),
        aliases: lines(form.aliases),
        scope: form.scope.trim() || "global",
        doc_types: form.doc_types,
        item_anchors: lines(form.anchors),
        provenance: "manual",
        by: name,
        notes: form.notes.trim(),
      };
      onCreated(await api.terminology.create(body));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="fixed inset-0 z-40 bg-black/30 flex items-center justify-center" onClick={onClose}>
      <div className="panel w-[36rem] max-w-[95vw]" onClick={(e) => e.stopPropagation()}>
        <div className="panel-title">New relationship (manual rule)</div>
        <div className="p-3 space-y-2 text-xs">
          <label className="block">
            <span className="text-gray-500">Canonical term (usually the label wording)</span>
            <input className="input w-full" value={form.canonical} onChange={(e) => setForm({ ...form, canonical: e.target.value })} autoFocus />
          </label>
          <label className="block">
            <span className="text-gray-500">Aliases (one per line; BOM / drawing wordings)</span>
            <textarea className="input w-full mono" rows={3} value={form.aliases} onChange={(e) => setForm({ ...form, aliases: e.target.value })} />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="text-gray-500">Scope</span>
              <input className="input w-full mono" value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })} placeholder="global | family:1295108 | sku:1295108NS" />
            </label>
            <label className="block">
              <span className="text-gray-500">Item anchors (optional)</span>
              <input className="input w-full mono" value={form.anchors} onChange={(e) => setForm({ ...form, anchors: e.target.value })} placeholder="4440003, 0703450" />
            </label>
          </div>
          <div>
            <span className="text-gray-500">Document types (none = all)</span>
            <div className="flex gap-3 mt-0.5">
              {DOC_TYPES.map((t) => (
                <label key={t} className="flex items-center gap-1">
                  <input type="checkbox" checked={form.doc_types.includes(t)} onChange={(e) => setForm({ ...form, doc_types: e.target.checked ? [...form.doc_types, t] : form.doc_types.filter((x) => x !== t) })} />
                  {t}
                </label>
              ))}
            </div>
          </div>
          <label className="block">
            <span className="text-gray-500">Notes — why this rule exists (source, who confirmed it)</span>
            <textarea className="input w-full" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </label>
          {!name && <div className="text-red-800">Enter your name in the top bar first.</div>}
          {err && <ErrorBox error={err} />}
        </div>
        <div className="px-3 py-2 border-t border-gray-200 flex justify-end gap-2">
          <button className="btn" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={submit} disabled={busy || !name || !form.canonical.trim() || lines(form.aliases).length === 0}>
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

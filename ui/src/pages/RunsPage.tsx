import { ArrowRight, ArrowClockwise, CircleNotch, FolderOpen, MagnifyingGlass, Plus, UploadSimple } from "@phosphor-icons/react";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useReviewer } from "../lib/reviewer";
import { api } from "../api";
import { RunActions } from "../components/RunActions";
import { RunDocumentsPicker } from "../components/RunDocumentsPicker";
import { Pagination } from "../components/Pagination";
import { usePagedList } from "../lib/pagination";
import { ErrorBox } from "../components/Feedback";
import { Button, Card, Dialog, EmptyState, PageHeader, TableSkeleton } from "../components/ui";
import { enc, fmtDate, displayName } from "../lib/format";
import { errorMessage, useAsync } from "../lib/useAsync";
import { supportedRunFiles, uploadProblem } from "../lib/uploads";
import { useDataRefresh } from "../lib/dataRefresh";
import type { RunSummary } from "../types";

export default function RunsPage() {
  const nav = useNavigate();
  const { session } = useReviewer();
  const [params, setParams] = useSearchParams();
  const tab = ["all", "mine", "shared", "deleted"].includes(params.get("view") ?? "") ? params.get("view")! : "all";
  const search = params.get("q") || "";
  const updateFilter = (key: string, value: string) => setParams(previous => { const next = new URLSearchParams(previous); value ? next.set(key, value) : next.delete(key); return next; }, { replace: true });
  const [creating, setCreating] = useState(false);
  const [runName, setRunName] = useState("");
  const health = useAsync(api.health, []);
  const runs = useAsync(() => api.listRuns(), []);
  useDataRefresh(runs.refresh);
  const deleted = useAsync(() => tab === "deleted" ? api.listDeletedRuns() : Promise.resolve([]), [tab]);
  useDataRefresh(deleted.refresh);
  const list = tab === "deleted" ? deleted : runs;
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [path, setPath] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [skippedFiles, setSkippedFiles] = useState(0);
  const fileCount = files.length;
  const problem = fileCount ? uploadProblem(files) : null;
  const selectFiles = (list: FileList) => {
    const supported = supportedRunFiles(Array.from(list ?? []));
    setFiles(supported);
    setSkippedFiles((list?.length ?? 0) - supported.length);
    setErr(list?.length && !supported.length ? uploadProblem(supported) : null);
  };
  const start = async (label: string, fn: () => Promise<RunSummary>) => {
    setBusy(label); setErr(null);
    try { const s = await fn(); nav(`/runs/${enc(s.run_id)}`); }
    catch (e) { setErr(errorMessage(e)); }
    finally { setBusy(null); }
  };
  const upload = () => {
    if (files.length) void start("upload", () => api.uploadRun(files, runName));
  };
  const all = runs.data ?? [];
  const visible = (tab === "deleted" ? deleted.data ?? [] : all).filter(r => (tab === "all" || tab === "deleted" || (tab === "mine" ? r.permission === "owner" : r.permission !== "owner")) && `${r.name} ${r.run_id} ${r.owner}`.toLowerCase().includes(search.toLowerCase()));
  const pagination = usePagedList(visible, `${tab}:${search}`);
  const openCreate = () => { setErr(null); setFiles([]); setSkippedFiles(0); setRunName(""); setPath(""); setCreating(true); };

  return <div className="workspace-page">
    <PageHeader title="Cross-checks" description="Open a run or upload documents to start a new check." actions={<Button variant="primary" onClick={openCreate} icon={<Plus size={18} />}>New cross-check</Button>} />
    <div className="workspace-summary" aria-label="Run totals">
      <div><span>Total runs</span><strong>{runs.data ? all.length : "—"}</strong></div>
      <div><span>My runs</span><strong>{runs.data ? all.filter(r => r.permission === "owner").length : "—"}</strong></div>
      <div><span>Shared with me</span><strong>{runs.data ? all.filter(r => r.permission !== "owner").length : "—"}</strong></div>
    </div>
    <section aria-label="Cross-check runs" className="runs-section">
      <div className="runs-heading"><h2>{tab === "deleted" ? "Deleted runs" : "Runs"} <span className="count-badge">{list.data ? list.data.length : "—"}</span></h2><Button size="sm" variant="ghost" onClick={list.reload} loading={list.loading} icon={<ArrowClockwise size={16} />}>Refresh</Button></div>
      <div className="runs-toolbar">
        <div className="view-switch" role="group" aria-label="Filter runs">{[["all", "All runs"], ["mine", "My runs"], ["shared", "Shared with me"], ["deleted", "Deleted runs"]].map(([value, label]) => <button key={value} aria-pressed={tab === value} onClick={() => { setErr(null); updateFilter("view", value); }}>{label}</button>)}</div>
        <label className="run-search"><MagnifyingGlass size={18} aria-hidden /><input value={search} onChange={e => updateFilter("q", e.target.value)} placeholder="Search runs…" aria-label="Search runs by name, ID or owner" />{search && <button onClick={() => updateFilter("q", "")} aria-label="Clear search">×</button>}</label>
      </div>
      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      {tab === "deleted" && err && <ErrorBox error={err} />}
      <Card className="runs-list">
        {list.loading && !list.data && <TableSkeleton rows={4} cols={4} />}
        {list.data && !visible.length && <EmptyState icon={<FolderOpen size={36} />} title={search ? "No matching runs" : tab === "deleted" ? "No deleted runs" : tab === "shared" ? "Nothing shared with you yet" : "No runs yet"} description={search ? "Try another name, run ID or owner, or clear your search." : tab === "deleted" ? "Runs you delete appear here. Only you can restore your runs." : tab === "shared" ? "When someone shares a run with you, it will appear here." : "Upload a project folder to create a run, or try the demo."} action={search ? <Button onClick={() => updateFilter("q", "")}>Clear search</Button> : tab === "deleted" ? undefined : <Button onClick={openCreate}>New cross-check</Button>} />}
        {!!visible.length && <><div className="run-list-labels" aria-hidden><span>Project / run</span><span>Documents</span><span>{tab === "deleted" ? "Recovery" : "Review status"}</span><span /></div>{pagination.rows.map(r => <article className="run-list-row" key={r.run_id}>
          <div className="run-title-cell"><span className="run-folder"><FolderOpen size={23} /></span><div className="min-w-0">{tab === "deleted" ? <span className="run-title">{r.name || r.run_id}</span> : <Link className="run-title" to={`/runs/${enc(r.run_id)}`}>{r.name || r.run_id}</Link>}<p>{tab === "deleted" ? `Deleted ${fmtDate(r.deleted_at || r.created_at)}` : fmtDate(r.created_at)} <span>·</span> {r.permission === "owner" ? "You own this run" : `Shared by ${displayName(r.owner || "Unknown owner")}`}</p><span className="run-access">{r.permission === "owner" ? "Owner" : r.permission === "edit" ? "Can edit" : "View only"}</span></div></div>
          <div className="run-volume"><strong>{r.summary.documents} files</strong><small>{r.summary.skus} SKUs · {r.summary.rows} comparisons</small></div>
          <div className="run-status">{tab === "deleted" ? <small>Restoring keeps the review history and existing sharing.</small> : <><span className={`result-pill ${r.summary.review_progress?.pending || r.summary.review_progress?.unresolved_rows ? "needs-review" : "cleared"}`}>{r.unavailable ? "Saved run unavailable" : r.summary.review_progress?.pending ? `${r.summary.review_progress.pending} awaiting review or approval` : r.summary.review_progress?.unresolved_rows ? `${r.summary.review_progress.unresolved_rows} unresolved findings` : "No pending reviews"}</span><small>{r.summary.review_progress?.approved ?? 0} approved · {r.summary.auto_cleared ?? 0} auto-cleared by engine</small></>}</div>
          <div className="run-row-actions">{tab === "deleted" ? <Button loading={busy === r.run_id} disabled={!!busy} onClick={async () => { setBusy(r.run_id); setErr(null); try { await api.restoreRun(r.run_id); } catch (e) { setErr(errorMessage(e)); } finally { setBusy(null); } }}>Restore run</Button> : <><RunActions run={r} compact onChanged={runs.reload} /><Link className="run-open" to={`/runs/${enc(r.run_id)}`} aria-label={`Open ${r.name || r.run_id}`}><span>Open run</span><ArrowRight size={18} /></Link></>}</div>
        </article>)}</>}
        <Pagination {...pagination} onChange={pagination.setOffset} label="Runs" />
      </Card>

    </section>
    <Dialog className="new-run-dialog" open={creating} onClose={() => { if (!busy) setCreating(false); }} title="New cross-check" description="Choose a folder or files containing your BOMs, labels, drawings and PCOs." footer={<><Button disabled={!!busy} onClick={() => setCreating(false)}>Cancel</Button><Button variant="primary" loading={busy === "upload"} disabled={!!busy || !fileCount || !!problem} onClick={upload} icon={<UploadSimple size={17} />}>{fileCount ? `Check ${fileCount} ${fileCount === 1 ? "file" : "files"}` : "Start cross-check"}</Button></>}>
      <div className="run-name-field"><label className="label" htmlFor="run-name">Run name <span className="text-ink-3">(optional)</span></label><input id="run-name" className="input w-full" disabled={!!busy} maxLength={120} placeholder="e.g. Orion · September label review" value={runName} onChange={e => setRunName(e.target.value)} /></div>
      <RunDocumentsPicker files={files} disabled={!!busy} onSelect={selectFiles} onRemove={index => setFiles(previous => previous.filter((_, i) => i !== index))} onClear={() => { setFiles([]); setSkippedFiles(0); setErr(null); }} />
      {!!skippedFiles && <p className="text-sm text-ink-3" role="status">{skippedFiles} unsupported or hidden {skippedFiles === 1 ? "file was" : "files were"} skipped. Supported formats: PDF, XLSX, XLSM and CSV.</p>}
      <div className="demo-option"><div><strong>Sample documents</strong><p>Use the demo to see how a review works.</p></div><Button disabled={!!busy} loading={busy === "demo"} onClick={() => start("demo", api.loadDemo)}>Try a demo</Button></div>
      {session?.is_admin && health.data && !health.data.hosted && <details className="advanced-options"><summary>Advanced: use a local folder path</summary><div className="space-y-3 pt-3"><p className="text-ink-3">Enter a folder path on the machine running Kaizen.</p><input className="input w-full mono" placeholder="/path/to/project-folder" disabled={!!busy} value={path} aria-label="Local folder path" onChange={e => setPath(e.target.value)} /><Button loading={busy === "path"} disabled={!!busy || !path.trim()} onClick={() => start("path", () => api.runFromPath(path.trim(), runName))}>Run folder</Button></div></details>}
      {busy && <p className="flex gap-2 items-center" role="status"><CircleNotch size={16} className="animate-spin" />Checking documents…</p>}
      {err && <ErrorBox error={err} />}
      {problem && <ErrorBox error={problem} />}
    </Dialog>
  </div>;
}

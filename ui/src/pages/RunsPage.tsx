import { ArrowRight, ArrowClockwise, Files, FolderOpen, MagnifyingGlass, Plus, UploadSimple, X } from "@phosphor-icons/react";
import { useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useReviewer } from "../lib/reviewer";
import { api, type RunProgress } from "../api";
import { RunActions } from "../components/RunActions";
import { Pagination } from "../components/Pagination";
import { usePagedList } from "../lib/pagination";
import { RunProgressIndicator } from "../components/RunProgressIndicator";
import { ErrorBox } from "../components/Feedback";
import { Button, Card, Dialog, EmptyState, PageHeader, TableSkeleton } from "../components/ui";
import { enc, fmtDate, displayName } from "../lib/format";
import { errorMessage, useAsync } from "../lib/useAsync";
import { addFileSet, addFolders, folderProblem, supportedRunFiles, uploadProblem, type UploadFolder } from "../lib/uploads";
import { useDataRefresh } from "../lib/dataRefresh";
import { useToast } from "../lib/toast";
import type { RunSummary } from "../types";

const DIR_PROPS = { webkitdirectory: "", directory: "" } as Record<string, string>;

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
  useDataRefresh(runs.reload);
  const deleted = useAsync(() => tab === "deleted" ? api.listDeletedRuns() : Promise.resolve([]), [tab]);
  useDataRefresh(deleted.reload);
  const list = tab === "deleted" ? deleted : runs;
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [path, setPath] = useState("");
  const [skippedFiles, setSkippedFiles] = useState(0);
  const [folders, setFolders] = useState<UploadFolder[]>([]);
  const folderInput = useRef<HTMLInputElement>(null);
  const filesInput = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [failure, setFailure] = useState<{ title: string; message: string } | null>(null);
  const toast = useToast();
  const fileCount = folders.reduce((total, folder) => total + folder.files.length, 0);
  const problem = folders.length ? uploadProblem(folders) : null;
  const selectFolder = (input: HTMLInputElement) => {
    const picked = Array.from(input.files ?? []);
    input.value = "";  // so choosing the same folder again still fires a change
    if (!picked.length) return;
    setSkippedFiles(picked.length - supportedRunFiles(picked).length);
    const next = addFolders(folders, picked);
    setFolders(next);
    setErr(next.length === folders.length ? (supportedRunFiles(picked).length ? "That folder is already added." : "That folder has no PDF, XLSX, XLSM or CSV documents.") : null);
  };
  const selectFiles = (input: HTMLInputElement) => {
    const picked = Array.from(input.files ?? []);
    input.value = "";
    if (!picked.length) return;
    setSkippedFiles(picked.length - supportedRunFiles(picked).length);
    const added = addFileSet(folders, picked);
    setFolders(added.folders);
    setErr(added.problem);
  };
  const showComplete = async () => { setProgress({percent: 100, stage: "Complete"}); await new Promise(resolve => window.setTimeout(resolve, 300)); };
  const start = async (label: string, fn: (onProgress: (value: RunProgress) => void) => Promise<RunSummary>) => {
    setBusy(label); setErr(null); setFailure(null); setProgress({percent: 0, stage: "Preparing documents"});
    try { const s = await fn(setProgress); await showComplete(); nav(`/runs/${enc(s.run_id)}`); }
    catch (e) { setProgress(null); setErr(errorMessage(e)); }
    finally { setBusy(null); }
  };
  // Every folder or 3-file set is its own run, sent one at a time so one bad set does not stop the rest.
  const upload = async () => {
    setBusy("upload"); setErr(null); setFailure(null); setProgress({percent: 0, stage: "Uploading documents"});
    const failed: UploadFolder[] = [], problems: string[] = [];
    let last: RunSummary | null = null;
    for (const [index, folder] of folders.entries()) {
      const update = (value: RunProgress) => setProgress({percent: Math.min(99, Math.floor((index * 100 + value.percent) / folders.length)), stage: `${folder.name}: ${value.stage}`});
      const label = folder.name.split("/").pop()!, typed = runName.trim();
      try { last = await api.uploadRun([folder], typed ? (folders.length === 1 ? typed : `${typed} · ${label}`) : label, update); }
      catch (e) { failed.push(folder); problems.push(`${folder.name}: ${errorMessage(e)}`); }
    }
    if (!failed.length) await showComplete();
    else setProgress(null);
    setBusy(null);
    const created = folders.length - failed.length;
    if (created) runs.reload();
    if (failed.length) {
      setFolders(failed);
      const notChecked = `${failed.length} ${failed.length === 1 ? "folder" : "folders"} could not be checked`;
      setFailure({ title: created ? `Created ${created} run${created === 1 ? "" : "s"} · ${notChecked}` : notChecked, message: `${problems.join("\n")}\n\nFix ${failed.length === 1 ? "it" : "them"} and try again, or remove ${failed.length === 1 ? "it" : "them"} from the list.` });
    } else if (created === 1 && last) nav(`/runs/${enc(last.run_id)}`);
    else { setCreating(false); toast({ tone: "ok", title: `Created ${created} runs`, description: "One run per folder." }); }
  };
  const runFromPath = async () => {
    setBusy("path"); setErr(null); setFailure(null); setProgress({percent: 0, stage: "Preparing documents"});
    try {
      const result = await api.runFromPath(path.trim(), runName, setProgress);
      if (result.failures.length) {
        runs.reload(); setProgress(null);
        setPath(result.failures[0].path);
        setFailure({title: `Created ${result.runs.length} run${result.runs.length === 1 ? "" : "s"} · ${result.failures.length} folder${result.failures.length === 1 ? "" : "s"} could not be checked`, message: result.failures.map(f => `${f.path}: ${f.message}`).join("\n") + "\nOnly failed folders are listed. Run a failed folder's path to retry it."});
        return;
      }
      const created = result.runs;
      await showComplete();
      if (created.length === 1) { nav(`/runs/${enc(created[0].run_id)}`); return; }
      runs.reload(); setCreating(false);
      toast({ tone: "ok", title: `Created ${created.length} runs`, description: "One run per folder." });
    }
    catch (e) { setProgress(null); setErr(errorMessage(e)); }
    finally { setBusy(null); }
  };
  const all = runs.data ?? [];
  const visible = (tab === "deleted" ? deleted.data ?? [] : all).filter(r => (tab === "all" || tab === "deleted" || (tab === "mine" ? r.permission === "owner" : r.permission !== "owner")) && `${r.name} ${r.run_id} ${r.owner}`.toLowerCase().includes(search.toLowerCase()));
  const pagination = usePagedList(visible, `${tab}:${search}`);
  const openCreate = () => { setErr(null); setFolders([]); setSkippedFiles(0); setFailure(null); setProgress(null); setRunName(""); setPath(""); setCreating(true); };

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
          <div className="run-row-actions">{tab === "deleted" ? <Button loading={busy === r.run_id} disabled={!!busy} onClick={async () => { setBusy(r.run_id); setErr(null); try { await api.restoreRun(r.run_id); } catch (e) { setProgress(null); setErr(errorMessage(e)); } finally { setBusy(null); } }}>Restore run</Button> : <><RunActions run={r} compact onChanged={runs.reload} /><Link className="run-open" to={`/runs/${enc(r.run_id)}`} aria-label={`Open ${r.name || r.run_id}`}><span>Open run</span><ArrowRight size={18} /></Link></>}</div>
        </article>)}</>}
        <Pagination {...pagination} onChange={pagination.setOffset} label="Runs" />
      </Card>

    </section>
    <Dialog className="new-run-dialog" open={creating} onClose={() => { if (!busy) setCreating(false); }} title="New cross-check" description="Add folders or sets of 3 files. Each one becomes its own run and needs exactly 3 documents: a BOM, a label and a drawing." footer={<><Button disabled={!!busy} onClick={() => setCreating(false)}>Cancel</Button><div className="run-start-action"><Button variant="primary" loading={busy === "upload"} disabled={!!busy || !folders.length || !!problem} onClick={upload} icon={<UploadSimple size={17} />}>{folders.length > 1 ? `Create ${folders.length} runs` : "Start cross-check"}</Button>{busy === "upload" && progress && <RunProgressIndicator value={progress} />}</div></>}>
      <label className="label" htmlFor="run-name">Run name <span className="text-ink-3">(optional; each run is also named after its folder)</span></label><input id="run-name" className="input w-full" disabled={!!busy} maxLength={120} placeholder="e.g. Orion · September label review" value={runName} onChange={e => setRunName(e.target.value)} />
      <div className="upload-zone"><FolderOpen size={32} /><strong>Add kit documents</strong><p>Each run needs one BOM, one label and one drawing: choose a folder holding them, or select the 3 files together. Documents are recognised by their content, with file names used as a fallback.</p><input ref={folderInput} type="file" multiple {...DIR_PROPS} hidden aria-label="Project folder" disabled={!!busy} onChange={e => selectFolder(e.target)} /><input ref={filesInput} type="file" multiple accept=".pdf,.xlsx,.xlsm,.csv" hidden aria-label="Individual documents" disabled={!!busy} onChange={e => selectFiles(e.target)} /><div className="flex flex-wrap justify-center gap-2"><Button variant={folders.length ? undefined : "primary"} disabled={!!busy} onClick={() => folderInput.current?.click()} icon={folders.length ? <Plus size={17} /> : <FolderOpen size={17} />}>{folders.length ? "Add a folder" : "Choose folder"}</Button><Button disabled={!!busy} onClick={() => filesInput.current?.click()} icon={<Files size={17} />}>{folders.length ? "Add 3 files" : "Choose 3 files"}</Button></div><small>PDF, XLSX, XLSM and CSV · Up to 250 MB per run · Choose a parent folder to add every folder inside it</small>{!!folders.length && <span role="status">{folders.length} run{folders.length === 1 ? "" : "s"} · {fileCount} documents</span>}</div>
      {!!skippedFiles && <p className="text-sm text-ink-3" role="status">{skippedFiles} unsupported or hidden files were skipped. Supported formats: PDF, XLSX, XLSM and CSV.</p>}
      {!!folders.length && <Button variant="ghost" size="sm" disabled={!!busy} onClick={() => { setFolders([]); setSkippedFiles(0); setFailure(null); setErr(null); }}>Clear all</Button>}
      {!!folders.length && <ul className="upload-folder-list space-y-3" aria-label="Runs to create">{folders.map(folder => { const issue = folderProblem(folder); const Icon = folder.loose ? Files : FolderOpen; return <li key={folder.name} className="flex items-start gap-3 text-sm"><Icon size={20} className={issue ? "text-bad-strong shrink-0" : "text-ok-strong shrink-0"} aria-hidden /><div className="min-w-0 flex-1"><strong className="block break-words">{folder.name || "(no folder)"}</strong><span className={issue ? "text-bad-strong" : "text-ink-3"}>{issue ?? `${folder.files.length} documents: ${folder.files.map(f => f.name).join(", ")}`}</span></div><Button size="sm" variant="ghost" disabled={!!busy} onClick={() => setFolders(folders.filter(f => f !== folder))} icon={<X size={16} />} aria-label={`Remove ${folder.name}`}>Remove</Button></li>; })}</ul>}
      <div className="demo-option"><div><strong>Sample documents</strong><p>Use the demo to see how a review works.</p></div><div className="run-start-action"><Button disabled={!!busy} loading={busy === "demo"} onClick={() => start("demo", api.loadDemo)}>Try a demo</Button>{busy === "demo" && progress && <RunProgressIndicator value={progress} />}</div></div>
      {session?.is_admin && health.data && !health.data.hosted && <details className="advanced-options"><summary>Advanced: use a local folder path</summary><div className="space-y-3 pt-3"><p className="text-ink-3">Enter a folder path on the machine running Kaizen.</p><input className="input w-full mono" placeholder="/path/to/project-folder" disabled={!!busy} value={path} aria-label="Local folder path" onChange={e => setPath(e.target.value)} /><div className="run-start-action"><Button loading={busy === "path"} disabled={!!busy || !path.trim()} onClick={() => void runFromPath()}>Run folder</Button>{busy === "path" && progress && <RunProgressIndicator value={progress} />}</div></div></details>}
      {err && <ErrorBox error={err} />}
      {failure && <ErrorBox title={failure.title} error={failure.message} />}
      {problem && <ErrorBox error={problem} />}
    </Dialog>
  </div>;
}

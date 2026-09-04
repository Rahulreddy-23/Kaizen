import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { ClassificationBadge } from "../components/Badges";
import { ErrorBox, Loading, Notice } from "../components/Feedback";
import { enc, fmtDate, shortSha } from "../lib/format";
import { errorMessage, useAsync } from "../lib/useAsync";
import { CLASSIFICATIONS, type RunSummary } from "../types";

// Folder selection: non-standard attributes, spread in to satisfy the React typings.
const DIR_PROPS = { webkitdirectory: "", directory: "" } as Record<string, string>;

export default function RunsPage() {
  const nav = useNavigate();
  const runs = useAsync(() => api.listRuns(), []);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [path, setPath] = useState("");
  const [fileCount, setFileCount] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);

  const start = async (label: string, fn: () => Promise<RunSummary>) => {
    setBusy(label);
    setErr(null);
    try {
      const s = await fn();
      nav(`/runs/${enc(s.run_id)}`);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  const upload = () => {
    const files = Array.from(fileRef.current?.files ?? []);
    if (files.length === 0) return;
    void start("upload", () => api.uploadRun(files));
  };
  const runPath = () => {
    if (!path.trim()) return;
    void start("path", () => api.runFromPath(path.trim()));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-3 flex-wrap">
        <h1>Runs</h1>
        <span className="text-xs text-gray-500">
          A run is one deterministic pass over a folder of documents. Same inputs, thresholds and terminology version give the same rows.
        </span>
      </div>

      <div className="grid md:grid-cols-3 gap-3">
        <div className="panel">
          <div className="panel-title">Load demo dataset</div>
          <div className="p-3 text-xs space-y-2">
            <p>Golden dataset: 10 SKUs (BOM, label, previous label, drawing, PCOs) with seeded discrepancies and ground truth.</p>
            <button className="btn btn-primary" disabled={busy !== null} onClick={() => start("demo", api.loadDemo)}>
              {busy === "demo" ? "Running…" : "Load demo dataset"}
            </button>
          </div>
        </div>
        <div className="panel">
          <div className="panel-title">Drop a folder</div>
          <div className="p-3 text-xs space-y-2">
            <p>Select the project folder that contains the SKU sub-folders and PCO spreadsheets. Relative paths are preserved for grouping.</p>
            <input ref={fileRef} type="file" multiple {...DIR_PROPS} className="text-xs block" onChange={(e) => setFileCount(e.target.files?.length ?? 0)} />
            <button className="btn btn-primary" disabled={busy !== null || fileCount === 0} onClick={upload}>
              {busy === "upload" ? "Uploading and running…" : `Upload ${fileCount || ""} file${fileCount === 1 ? "" : "s"} and run`}
            </button>
          </div>
        </div>
        <div className="panel">
          <div className="panel-title">Run a local folder path</div>
          <div className="p-3 text-xs space-y-2">
            <p>Path on this machine as seen by the API process (nothing is uploaded).</p>
            <input
              className="input w-full mono"
              placeholder="/path/to/project-folder"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") runPath();
              }}
            />
            <button className="btn btn-primary" disabled={busy !== null || !path.trim()} onClick={runPath}>
              {busy === "path" ? "Running…" : "Run folder"}
            </button>
          </div>
        </div>
      </div>

      {busy && <Notice>Running the cross-check: parsing every document and running the five checks. This takes a few seconds per SKU.</Notice>}
      {err && <ErrorBox error={err} />}

      <div className="panel">
        <div className="panel-title">
          Previous runs {runs.data && <span className="normal-case font-normal text-gray-500">({runs.data.length})</span>}
          <button className="btn btn-sm ml-auto" onClick={runs.reload}>
            Refresh
          </button>
        </div>
        {runs.loading && !runs.data && <Loading />}
        {runs.error && (
          <div className="p-3">
            <ErrorBox error={runs.error} onRetry={runs.reload} />
          </div>
        )}
        {runs.data &&
          (runs.data.length === 0 ? (
            <div className="p-3 text-xs text-gray-500">No runs yet. Load the demo dataset or drop a folder.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Created</th>
                    <th>Input</th>
                    <th className="text-right">SKUs</th>
                    <th className="text-right">Docs</th>
                    <th className="text-right">Rows</th>
                    <th className="text-right">Needs review</th>
                    <th className="text-right">Auto-cleared</th>
                    <th>By classification</th>
                    <th>Tool</th>
                    <th>Terminology</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data.map((r) => (
                    <tr key={r.run_id} className="clickable" onClick={() => nav(`/runs/${enc(r.run_id)}`)}>
                      <td className="mono">
                        <Link to={`/runs/${enc(r.run_id)}`} className="underline">
                          {r.run_id}
                        </Link>
                      </td>
                      <td className="whitespace-nowrap">{fmtDate(r.created_at)}</td>
                      <td className="mono text-gray-600 max-w-[18rem] truncate" title={r.input_root}>{r.input_root}</td>
                      <td className="text-right tabular-nums">{r.summary.skus}</td>
                      <td className="text-right tabular-nums">{r.summary.documents}</td>
                      <td className="text-right tabular-nums">{r.summary.rows}</td>
                      <td className="text-right tabular-nums text-red-800 font-semibold">{r.summary.needs_validation}</td>
                      <td className="text-right tabular-nums text-green-800">{r.summary.rows - r.summary.needs_validation}</td>
                      <td className="whitespace-nowrap">
                        {CLASSIFICATIONS.map((c) => (
                          <span key={c} className="mr-2 inline-flex items-center gap-1">
                            <ClassificationBadge value={c} />
                            <span className="tabular-nums">{r.summary[c] ?? 0}</span>
                          </span>
                        ))}
                      </td>
                      <td>{r.tool_version}</td>
                      <td className="mono text-gray-500" title={r.terminology_version}>
                        {shortSha(r.terminology_version)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </div>
    </div>
  );
}

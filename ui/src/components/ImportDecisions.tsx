// Optional Excel round-trip. Reviewers who prefer to work offline fill the decision columns in the exported
// workbook and import them here. Preview first (a dry run writes nothing); conflicts are never overwritten
// unless the reviewer ticks "overwrite".
import { useState } from "react";
import { api } from "../api";
import { useReviewer } from "../lib/reviewer";
import { errorMessage } from "../lib/useAsync";
import type { RoundTripResult } from "../types";
import { ErrorBox } from "./Feedback";

export function ImportDecisions({ runId, onApplied }: { runId: string; onApplied: () => void }) {
  const { session } = useReviewer();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<RoundTripResult | null>(null);
  const [result, setResult] = useState<RoundTripResult | null>(null);
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState<"preview" | "apply" | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = async (dryRun: boolean) => {
    if (!file) return;
    setBusy(dryRun ? "preview" : "apply");
    setErr(null);
    try {
      const r = await api.importDecisions(runId, file, { dryRun, force });
      if (dryRun) setPreview(r);
      else {
        setResult(r);
        setPreview(null);
        onApplied();
      }
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  if (!open) {
    return (
      <button className="btn" onClick={() => setOpen(true)} title="Optional: apply decisions you recorded in the exported workbook">
        Import decisions from Excel…
      </button>
    );
  }
  return (
    <div className="panel p-3 space-y-2 text-xs">
      <div className="flex items-center gap-2">
        <b>Import decisions from Excel</b>
        <span className="chip">optional</span>
        <button className="btn btn-sm ml-auto" onClick={() => setOpen(false)}>
          Close
        </button>
      </div>
      <p className="text-gray-600">
        Export the workbook, fill the <b>Reviewer {session?.slot === 2 ? "2 " : ""}Decision</b> and comment columns (an override is written as <span className="mono">OVERRIDE→EQUIVALENT</span>), then
        import it here. Only your own columns are read; the workbook must belong to this run; values are validated; a decision changed in the tool after the export is a conflict and is not overwritten
        unless you say so. Every applied decision is audited under your name ({session?.reviewer}).
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        <input
          type="file"
          accept=".xlsx"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setPreview(null);
            setResult(null);
          }}
        />
        <button className="btn" disabled={!file || busy !== null} onClick={() => run(true)}>
          {busy === "preview" ? "Checking…" : "Preview (dry run)"}
        </button>
        <button className="btn btn-primary" disabled={!file || busy !== null || !preview} onClick={() => run(false)} title="Applies what the preview listed">
          {busy === "apply" ? "Applying…" : "Apply"}
        </button>
        {preview && preview.conflicts.length > 0 && (
          <label className="flex items-center gap-1 text-red-800">
            <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} /> overwrite the {preview.conflicts.length} conflict(s)
          </label>
        )}
      </div>
      {err && <ErrorBox error={err} />}
      {(preview ?? result) && <Outcome r={(result ?? preview)!} />}
    </div>
  );
}

function Outcome({ r }: { r: RoundTripResult }) {
  return (
    <div className="space-y-1">
      <div className={`font-semibold ${r.dry_run ? "text-blue-800" : "text-green-800"}`}>{r.summary}</div>
      {r.conflicts.length > 0 && (
        <div>
          <div className="label">Conflicts (the tool changed these after the workbook was exported)</div>
          <ul className="list-disc pl-4">
            {r.conflicts.map((c) => (
              <li key={c.row_id}>
                <span className="mono">{c.row_id}</span>: workbook says <b>{c.workbook}</b>, tool has <b>{c.database}</b> by {c.database_reviewer} at {c.database_decided_at}
              </li>
            ))}
          </ul>
        </div>
      )}
      {r.invalid.length > 0 && (
        <div>
          <div className="label">Invalid values (not applied)</div>
          <ul className="list-disc pl-4">
            {r.invalid.map((i) => (
              <li key={i.row_id}>
                <span className="mono">{i.row_id}</span> ({i.sheet}): {i.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      {r.unknown_rows.length > 0 && (
        <div className="text-gray-600">
          Unknown row ids ignored: <span className="mono">{r.unknown_rows.join(", ")}</span>
        </div>
      )}
    </div>
  );
}

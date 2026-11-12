import { CaretDown, FileXls } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { fmtDate } from "../lib/format";
import type { RunVersion } from "../types";
import { Button } from "./ui";

export function versionLabel(version: RunVersion) {
  return `${version.rerun_number ? `Rerun ${version.rerun_number}` : "Original run"} · ${fmtDate(version.created_at)}`;
}

export function ExcelExport({ runId, quickSku }: { runId: string; quickSku?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const selectId = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLDivElement>(null);
  const [versions, setVersions] = useState<RunVersion[]>([]);
  const [picked, setPicked] = useState<string | null>(null);
  // Reruns are listed under the original run. Reload them each time the panel opens so a rerun that
  // just finished is offered; the newest version is selected unless the reviewer picked another.
  useEffect(() => {
    if (!open || quickSku !== undefined) return;
    let current = true;
    Promise.resolve().then(() => api.runVersions(runId)).then(list => { if (current) setVersions(list); }, () => { if (current) setVersions([]); });
    return () => { current = false; };
  }, [open, runId, quickSku]);
  const exportRunId = (picked && versions.some(v => v.run_id === picked) ? picked : versions[versions.length - 1]?.run_id) ?? runId;

  useEffect(() => {
    if (!open) return;
    root.current?.querySelector<HTMLAnchorElement>("a")?.focus();
    const dismiss = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);

  return (
    <div ref={root} className="excel-export" onBlur={event => {
      if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget as Node)) setOpen(false);
    }} onKeyDown={event => {
      if (event.key === "Escape" && open) {
        event.preventDefault();
        event.stopPropagation();
        setOpen(false);
        trigger.current?.querySelector<HTMLButtonElement>("button")?.focus();
      }
    }}>
      <div ref={trigger}>
        <Button icon={<FileXls size={16} />} iconRight={<CaretDown size={14} />} aria-expanded={open} aria-controls={open ? id : undefined} onClick={() => setOpen(value => !value)}>
          Download Excel
        </Button>
      </div>
      {open && <div id={id} className="excel-export-panel" role="region" aria-label="Excel download options">
        {quickSku !== undefined ? <>
        <p className="excel-export-note">BOM, Label and Diagram side by side</p>
        <a href={api.quickExportUrl(runId, quickSku)} download aria-label="Download this SKU comparison Excel" onClick={() => setOpen(false)}><span className="font-medium">This SKU · {quickSku}</span><span className="excel-export-description">All entries, matching status and original source text.</span></a>
        <a href={api.quickExportUrl(runId)} download aria-label="Download all SKUs comparison Excel" onClick={() => setOpen(false)}><span className="font-medium">All SKUs</span><span className="excel-export-description">One comparison worksheet per SKU, plus source details.</span></a>
        <p className="excel-export-note">Includes all entries. Screen filters are not applied. Read-only .xlsx; this comparison cannot be imported as decisions.</p>
        </> : <>{versions.length > 1 && <div className="excel-export-version">
          <label htmlFor={selectId}>Run version</label>
          <select id={selectId} className="input w-full" value={exportRunId} onChange={event => setPicked(event.target.value)}>
            {versions.map(v => <option key={v.run_id} value={v.run_id}>{versionLabel(v)}</option>)}
          </select>
          <p className="excel-export-description">Reruns process the same documents again. Review decisions stay with the version where they were made.</p>
        </div>}
        <p className="excel-export-note">One worksheet per SKU</p>
        <a href={api.exportUrl(exportRunId, "summary")} download aria-label="Download summary Excel" onClick={() => setOpen(false)}>
          <span className="font-medium">Summary</span>
          <span className="excel-export-description">Check totals, review status and rows needing attention.</span>
        </a>
        <a href={api.exportUrl(exportRunId, "complete")} download aria-label="Download complete details Excel" onClick={() => setOpen(false)}>
          <span className="font-medium">Complete details</span>
          <span className="excel-export-description">Every comparison, source evidence, decisions, approvals and supporting audit sheets.</span>
        </a>
        <p className="excel-export-note">Both downloads use .xlsx. Decision and comment columns can be imported back.</p>
        <p className="excel-export-note">BD cross-check format · three sheets per SKU</p>
        <a href={api.exportUrl(exportRunId, "bcc")} download aria-label="Download BCC template Excel" onClick={() => setOpen(false)}>
          <span className="font-medium">BCC template</span>
          <span className="excel-export-description">Label VS BOM, Drawings VS BOM and Combined sheets with match results, counts and approvals. Read-only.</span>
        </a></>}
      </div>}
    </div>
  );
}

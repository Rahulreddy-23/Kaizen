import { CaretDown, FileXls } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { Button } from "./ui";

export function ExcelExport({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLDivElement>(null);

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
        <p className="excel-export-note">One worksheet per SKU</p>
        <a href={api.exportUrl(runId, "summary")} download aria-label="Download summary Excel" onClick={() => setOpen(false)}>
          <span className="font-medium">Summary</span>
          <span className="excel-export-description">Check totals, review status and rows needing attention.</span>
        </a>
        <a href={api.exportUrl(runId, "complete")} download aria-label="Download complete details Excel" onClick={() => setOpen(false)}>
          <span className="font-medium">Complete details</span>
          <span className="excel-export-description">Every comparison, source evidence, decisions, approvals and supporting audit sheets.</span>
        </a>
        <p className="excel-export-note">Both downloads use .xlsx. Decision and comment columns can be imported back.</p>
      </div>}
    </div>
  );
}

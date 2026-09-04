import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { enc, fmtQty, isPdf, shortSha } from "../lib/format";
import type { Evidence } from "../types";
import { DocTypeBadge } from "./Badges";
import { PageImage } from "./PageImage";

interface Props {
  side: "A" | "B";
  runId: string;
  rowId: string;
  ev: Evidence | null;
  /** DocumentItem id (from the full result) so the document view can pre-select the row. */
  itemId?: string | null;
}

/** One side of a comparison: the source page (with highlight) and everything that was extracted from it. */
export function EvidenceCard({ side, runId, rowId, ev, itemId }: Props) {
  const [fit, setFit] = useState(true);
  if (!ev) {
    return (
      <div className="panel">
        <div className="panel-title">Source {side}</div>
        <div className="p-3 text-xs text-gray-600">No counterpart on this side: the engine found nothing to pair with.</div>
      </div>
    );
  }
  const hasPage = ev.page !== null && isPdf(ev.file_name);
  const src = hasPage ? api.pageImageUrl(runId, ev.doc_id, ev.page as number, rowId) : null;
  const docLink = `/runs/${enc(runId)}/documents/${enc(ev.doc_id)}?page=${ev.page ?? 1}${itemId ? `&item=${enc(itemId)}` : ""}`;
  const lowConf = ev.confidence < 0.7;
  const fallback = (
    <div className="space-y-1">
      <div className="text-gray-600">No page image for this source (spreadsheet). Locator and raw text:</div>
      <div className="mono">{ev.locator ?? "—"}</div>
      <pre className="mono whitespace-pre-wrap bg-gray-50 border border-gray-200 p-2">{ev.raw_text}</pre>
    </div>
  );
  return (
    <div className="panel">
      <div className="panel-title">
        <span>Source {side}</span>
        <DocTypeBadge value={ev.doc_type} />
        <span className="mono normal-case font-normal text-gray-700 truncate">{ev.file_name}</span>
        {ev.page !== null && <span className="normal-case font-normal">page {ev.page}</span>}
        <span className="ml-auto flex gap-1 normal-case font-normal">
          {src && (
            <>
              <button className="btn btn-sm" onClick={() => setFit(!fit)}>
                {fit ? "Actual size" : "Fit width"}
              </button>
              <a className="btn btn-sm" href={src} target="_blank" rel="noreferrer">
                Open page
              </a>
            </>
          )}
          <Link className="btn btn-sm" to={docLink}>
            Extraction view
          </Link>
        </span>
      </div>
      <div className="p-2">
        <PageImage src={src} bbox={ev.bbox} fit={fit} alt={`${ev.file_name} page ${ev.page ?? ""}`} fallback={fallback} />
        {src && ev.bbox === null && (
          <div className="text-2xs text-gray-500 mt-1">No bounding box for this value (for example a document header), so the page is shown without a highlight.</div>
        )}
      </div>
      <dl className="kv px-3 pb-3">
        <dt>Locator</dt>
        <dd>{ev.locator ?? "—"}{ev.sheet ? <span className="text-gray-500"> · sheet {ev.sheet}</span> : null}</dd>
        <dt>Item number</dt>
        <dd className="mono">{ev.item_number ?? "—"}</dd>
        <dt>Description</dt>
        <dd className="font-medium">{ev.description}</dd>
        <dt>Quantity</dt>
        <dd className="tabular-nums">
          {fmtQty(ev.quantity)} {ev.uom ?? ""}
          {ev.sub_quantity && <span className="text-gray-500"> · sub-quantity {ev.sub_quantity.raw}</span>}
          {ev.oper_seq && <span className="text-gray-500"> · seq {ev.oper_seq}</span>}
        </dd>
        <dt>Category</dt>
        <dd>
          {ev.category}
          {ev.category_reason && <span className="text-gray-500"> — {ev.category_reason}</span>}
        </dd>
        <dt>Extraction confidence</dt>
        <dd className={lowConf ? "text-amber-700 font-semibold" : ""}>
          {(ev.confidence * 100).toFixed(0)}%{lowConf && " (below threshold — verify against the page)"}
        </dd>
        <dt>Raw text</dt>
        <dd>
          <pre className="mono whitespace-pre-wrap bg-gray-50 border border-gray-200 p-1.5">{ev.raw_text}</pre>
        </dd>
        <dt>File</dt>
        <dd className="mono text-gray-500 break-all">
          {ev.file}
          <br />
          sha256 {shortSha(ev.sha256, 16)}…
        </dd>
      </dl>
    </div>
  );
}

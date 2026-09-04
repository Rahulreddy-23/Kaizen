import { useMemo, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { DocTypeBadge } from "../components/Badges";
import { ErrorBox, Loading } from "../components/Feedback";
import { PageImage } from "../components/PageImage";
import { enc, fmtQty, isPdf } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { DocType, DocumentItem } from "../types";

interface Col {
  h: string;
  cell: (i: DocumentItem) => ReactNode;
  cls?: string;
}

const str = (v: unknown) => (v === null || v === undefined || v === "" ? "—" : String(v));

function columns(t: DocType): Col[] {
  switch (t) {
    case "BOM":
      return [
        { h: "Item number", cell: (i) => i.item_number ?? "—", cls: "mono whitespace-nowrap" },
        { h: "Description", cell: (i) => i.description },
        { h: "Qty", cell: (i) => `${fmtQty(i.quantity)} ${i.uom ?? ""}`, cls: "tabular-nums whitespace-nowrap text-right" },
        { h: "Seq", cell: (i) => i.oper_seq ?? "—", cls: "tabular-nums" },
        {
          h: "Category",
          cell: (i) => (
            <>
              <span className={i.category === "PHYSICAL_COMPONENT" ? "font-semibold" : "text-gray-600"}>{i.category}</span>
              {i.category_reason && <div className="text-2xs text-gray-500">{i.category_reason}</div>}
            </>
          ),
        },
        { h: "Active", cell: (i) => (i.is_active ? "yes" : <span className="text-gray-400">no</span>) },
        { h: "Locator", cell: (i) => i.locator ?? "—", cls: "text-gray-500 whitespace-nowrap" },
      ];
    case "LABEL":
      return [
        { h: "Qty", cell: (i) => `${fmtQty(i.quantity)} ${i.uom ?? ""}`, cls: "tabular-nums whitespace-nowrap" },
        { h: "Description", cell: (i) => i.description },
        { h: "Sub-quantity", cell: (i) => (i.sub_quantity ? `${i.sub_quantity.raw} (${i.sub_quantity.value} ${i.sub_quantity.kind})` : "—"), cls: "text-gray-600" },
        { h: "Category", cell: (i) => i.category, cls: "text-gray-600" },
        { h: "Locator", cell: (i) => i.locator ?? "—", cls: "text-gray-500 whitespace-nowrap" },
      ];
    case "DRAWING":
      return [
        { h: "Callout", cell: (i) => str(i.attributes.callout_index), cls: "tabular-nums" },
        { h: "Sheet", cell: (i) => str(i.attributes.sheet), cls: "tabular-nums" },
        { h: "Text (EN)", cell: (i) => i.description },
        { h: "Spanish text", cell: (i) => str(i.attributes.es_text), cls: "text-gray-700" },
        { h: "Conditional", cell: (i) => (i.attributes.conditional ? <span className="text-amber-800 font-semibold">yes</span> : "no") },
        { h: "Placement", cell: (i) => str(i.attributes.placement), cls: "text-gray-600" },
      ];
    case "PCO":
      return [
        {
          h: "Kind",
          cell: (i) => (
            <>
              <span className="mono">{str(i.attributes.kind)}</span>
              {i.attributes.change_kind ? <span className="chip ml-1">{String(i.attributes.change_kind)}</span> : null}
            </>
          ),
          cls: "whitespace-nowrap",
        },
        {
          h: "Item actual → proposed",
          cell: (i) => (i.attributes.kind === "change" ? `${str(i.attributes.item_actual)} → ${str(i.attributes.item_proposed)}` : i.item_number ?? "—"),
          cls: "mono whitespace-nowrap",
        },
        { h: "Description", cell: (i) => i.description },
        { h: "Qty actual → proposed", cell: (i) => (i.attributes.kind === "change" ? `${str(i.attributes.qty_actual)} → ${str(i.attributes.qty_proposed)}` : "—"), cls: "tabular-nums whitespace-nowrap" },
        { h: "Seq actual → proposed", cell: (i) => (i.attributes.kind === "change" ? `${str(i.attributes.seq_actual)} → ${str(i.attributes.seq_proposed)}` : "—"), cls: "tabular-nums whitespace-nowrap" },
        { h: "Locator", cell: (i) => i.locator ?? "—", cls: "text-gray-500 whitespace-nowrap" },
      ];
  }
}

export default function DocumentPage() {
  const { runId = "", docId = "" } = useParams();
  const [sp, setSp] = useSearchParams();
  const doc = useAsync(() => api.getDocumentItems(runId, docId), [runId, docId]);
  const page = Math.max(1, Number(sp.get("page") || 1) || 1);
  const selectedId = sp.get("item");
  const selected = useMemo(() => doc.data?.items.find((i) => i.id === selectedId) ?? null, [doc.data, selectedId]);

  const setParam = (k: string, v: string | null) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v);
    else n.delete(k);
    setSp(n, { replace: true });
  };
  const select = (i: DocumentItem) => {
    const n = new URLSearchParams(sp);
    n.set("item", i.id);
    if (i.page) n.set("page", String(i.page));
    setSp(n, { replace: true });
  };

  if (doc.error) return <ErrorBox error={doc.error} onRetry={doc.reload} />;
  if (!doc.data) return <Loading label="Loading document…" />;
  const d = doc.data;
  const pdf = isPdf(d.file_name) && d.pages > 0;
  const src = pdf ? api.pageImageUrl(runId, docId, page) : null;
  const cols = columns(d.doc_type);
  const lowConf = d.items.filter((i) => i.confidence < 0.7).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <Link className="btn" to={`/runs/${enc(runId)}/documents`}>
          ← Documents
        </Link>
        <DocTypeBadge value={d.doc_type} />
        <h1 className="mono">{d.file_name}</h1>
        <span className="text-xs text-gray-500">
          {d.items.length} extracted items · {pdf ? `${d.pages} page${d.pages === 1 ? "" : "s"}` : "spreadsheet source (no page images)"}
          {lowConf > 0 && <span className="text-amber-800"> · {lowConf} below the confidence threshold</span>}
        </span>
        <span className="text-xs text-gray-500 ml-auto">Click an extracted row to outline where it came from on the page.</span>
      </div>

      {d.warnings.length > 0 && (
        <div className="border border-amber-600 bg-amber-50 text-amber-900 text-xs px-3 py-2">
          <b>Parser warnings:</b>
          <ul className="list-disc pl-4">
            {d.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid xl:grid-cols-2 gap-3 items-start">
        <div className="panel">
          <div className="panel-title">
            Source page
            {pdf && (
              <span className="ml-auto flex items-center gap-1 normal-case font-normal">
                <button className="btn btn-sm" disabled={page <= 1} onClick={() => setParam("page", String(page - 1))}>
                  ←
                </button>
                <select className="input" value={page} onChange={(e) => setParam("page", e.target.value)}>
                  {Array.from({ length: d.pages }, (_, i) => i + 1).map((n) => (
                    <option key={n} value={n}>
                      page {n} / {d.pages}
                    </option>
                  ))}
                </select>
                <button className="btn btn-sm" disabled={page >= d.pages} onClick={() => setParam("page", String(page + 1))}>
                  →
                </button>
                {src && (
                  <a className="btn btn-sm" href={src} target="_blank" rel="noreferrer">
                    Open
                  </a>
                )}
              </span>
            )}
          </div>
          <div className="p-2">
            <PageImage
              src={src}
              bbox={selected && selected.page === page ? selected.bbox : null}
              alt={`${d.file_name} page ${page}`}
              maxHeight="78vh"
              fallback={
                <div>
                  <div className="text-gray-600">No page image: this source is a spreadsheet. Each extracted row shows its sheet/row locator and the raw cell text instead.</div>
                  {selected && (
                    <div className="mt-2">
                      <div className="label">Selected row</div>
                      <div className="mono">{selected.locator}</div>
                      <pre className="mono whitespace-pre-wrap bg-gray-50 border border-gray-200 p-2 mt-1">{selected.raw_text}</pre>
                    </div>
                  )}
                </div>
              }
            />
            {selected && (
              <div className="text-2xs text-gray-600 mt-1">
                Selected <span className="mono">{selected.id}</span> · {selected.locator} · confidence {(selected.confidence * 100).toFixed(0)}%
                {selected.bbox === null && " · no bounding box recorded"}
                {selected.page !== null && selected.page !== page && ` · on page ${selected.page}`}
              </div>
            )}
          </div>
          {Object.keys(d.header).length > 0 && (
            <div className="border-t border-gray-200 px-3 py-2">
              <div className="label mb-1">Document header</div>
              <dl className="kv">
                {Object.entries(d.header).map(([k, v]) => (
                  <div key={k} className="contents">
                    <dt className="mono">{k}</dt>
                    <dd>{Array.isArray(v) ? v.join(", ") : str(v)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-title">Extracted structure ({d.items.length})</div>
          <div className="max-h-[85vh] overflow-auto">
            <table className="tbl">
              <thead className="sticky top-0">
                <tr>
                  <th>#</th>
                  {cols.map((c) => (
                    <th key={c.h}>{c.h}</th>
                  ))}
                  <th className="text-right">Conf.</th>
                </tr>
              </thead>
              <tbody>
                {d.items.map((i, n) => (
                  <tr key={i.id} className={`clickable ${i.id === selectedId ? "selected" : ""} ${i.is_active ? "" : "text-gray-400"}`} onClick={() => select(i)}>
                    <td className="tabular-nums text-gray-500">{n + 1}</td>
                    {cols.map((c) => (
                      <td key={c.h} className={c.cls}>
                        {c.cell(i)}
                      </td>
                    ))}
                    <td className={`text-right tabular-nums ${i.confidence < 0.7 ? "text-amber-800 font-semibold" : "text-gray-500"}`}>{(i.confidence * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selected && (
            <div className="border-t border-gray-200 px-3 py-2">
              <div className="label mb-1">Raw text of the selected row</div>
              <pre className="mono whitespace-pre-wrap bg-gray-50 border border-gray-200 p-2">{selected.raw_text}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

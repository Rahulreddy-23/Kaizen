import { ArrowsClockwise, Circle, MagnifyingGlass } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox } from "../components/Feedback";
import { QuickDocumentWorkspace } from "../components/QuickDocumentWorkspace";
import { ExcelExport } from "../components/ExcelExport";
import { QUICK_KINDS as KINDS, QUICK_NAME as NAME, QuickStatusLabel as Status } from "../components/QuickStatus";
import { Pagination } from "../components/Pagination";
import { Button, EmptyState, LinkButton, PageHeader, TableSkeleton } from "../components/ui";
import { enc, fmtQty, issueLabel } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useDataRefresh } from "../lib/dataRefresh";
import type { QuickKind, QuickRow, QuickView } from "../types";

const PAIR: Record<string, string> = {BOM_LABEL: "BOM ↔ Label", BOM_DRAWING: "BOM ↔ Diagram", LABEL_DRAWING: "Label ↔ Diagram"};

export default function QuickViewPage() {
  const {runId = ""} = useParams();
  const [params, setParams] = useSearchParams();
  const currentParams = useRef(params);
  currentParams.current = params;
  const sku = params.get("sku") || "";
  const view = params.get("view") === "text" ? "text" : "components";
  const rawStatus = params.get("status") || "compared";
  const status = ["all", "compared", "matched", "attention", "neutral"].includes(rawStatus) ? rawStatus : "compared";
  const requestedOffset = Number(params.get("offset"));
  const offset = Number.isFinite(requestedOffset) ? Math.max(0, Math.floor(requestedOffset)) : 0;
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [selected, setSelected] = useState<QuickRow | null>(null);
  const [focusItems, setFocusItems] = useState<Partial<Record<QuickKind,string>>>({});
  const preview = useRef<HTMLElement>(null);
  const matrix = useRef<HTMLDivElement>(null);
  useEffect(() => { const timer = window.setTimeout(() => setSearch(query), 200); return () => window.clearTimeout(timer); }, [query]);
  const data = useAsync(() => api.quickView(runId, {sku, view, status: view === "text" ? "all" : status, search, offset}), [runId, sku, view, status, search, offset]);
  const [cached, setCached] = useState<{runId:string; sku:string; value:QuickView} | null>(null);
  useEffect(() => {if (data.data) setCached({runId,sku,value:data.data});}, [data.data,runId,sku]);
  useDataRefresh(data.reload, runId);
  useEffect(() => {setExpanded(false);}, [runId, sku]);
  useEffect(() => {setSelected(null); setFocusItems({});}, [runId, sku, view, status, search, offset]);
  // A refreshed decision must replace the selected row's old status and evidence.
  useEffect(() => {setSelected(old => old ? data.data?.rows.find(r => r.id === old.id) ?? null : null);}, [data.data]);
  const change = (key: string, value: string) => {
    setSelected(null);
    const next = new URLSearchParams(currentParams.current);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "offset") next.delete("offset");
    currentParams.current = next;
    setParams(next);
  };
  const choose = (row: QuickRow, kind?: QuickKind, itemId?: string) => {
    setSelected(row);
    setFocusItems(kind && itemId ? {[kind]:itemId} : {});
    if (!expanded) window.requestAnimationFrame(() => preview.current?.scrollIntoView?.({block:"start"}));
  };
  // Retain controls while filters load, but never carry source data into another
  // SKU/run. Old rows are disabled/hidden until the new response is available.
  const result = data.data ?? (cached?.runId === runId && cached.sku === sku ? cached.value : null);
  const groups = result?.groups ?? (cached?.runId === runId ? cached.value.groups : []);
  const activeSku = result?.sku || sku;
  const warnings = result?.documents.reduce((n,d) => n + d.warnings.length, 0) ?? 0;
  const selectedIndex = result?.rows.findIndex(row => row.id === selected?.id) ?? -1;
  const entryNavigation = selected && result && <div className="quick-entry-navigation">
    <div><strong>{selected.cells.BOM?.items[0]?.description || selected.cells.LABEL?.items[0]?.description || selected.cells.DRAWING?.items[0]?.description}</strong><span>Entry {offset + selectedIndex + 1} of {result.total} · <Status status={selected.status} /></span></div>
    <div className="flex gap-2"><Button size="sm" disabled={data.loading || selectedIndex <= 0} onClick={() => choose(result.rows[selectedIndex - 1])}>Previous entry</Button><Button size="sm" disabled={data.loading || selectedIndex < 0 || selectedIndex >= result.rows.length - 1} onClick={() => choose(result.rows[selectedIndex + 1])}>Next entry</Button></div>
  </div>;
  const comparisonDetails = selected && selected.checks.length > 0 && <details className="quick-checks"><summary>Comparison details · {selected.checks.length} checks</summary><div>{selected.checks.map(check => <div key={check.row_id} className="quick-check"><Status status={check.status} /><Link to={`/runs/${enc(runId)}/rows/${enc(check.row_id)}`}>{PAIR[check.check] || check.check} · {check.state === "FINALIZED" ? "Approved" : "Engine / pending review"}</Link><p>{check.explanation}</p>{check.merged_rows > 1 && <p>{check.merged_rows} BOM rows combined by the comparison; individual source rows are shown above.</p>}{check.findings.map((f,n) => <p key={n}>{issueLabel(f.type)}: {f.detail}</p>)}</div>)}</div></details>;

  return <div className="quick-view">
    <PageHeader back={{to:`/runs/${enc(runId)}`,label:"Overview"}} title="Quick view"
      description="Compare one SKU across its BOM, label and diagram. Select an entry to locate the source text."
      actions={<>{result?.can_export && activeSku && <ExcelExport key={`${runId}:${activeSku}`} runId={runId} quickSku={activeSku}/>}<Button icon={<ArrowsClockwise size={16} />} onClick={data.reload} loading={data.loading}>Refresh</Button></>} />
    <nav className="quick-skus" aria-label="SKU selection">
      {groups.map((g, n) => <button key={g.sku} className={`quick-sku ${activeSku === g.sku ? "is-active" : ""}`} aria-pressed={activeSku === g.sku} onClick={() => change("sku", g.sku)}><strong>SKU {n + 1}</strong><span>{g.sku}</span></button>)}
    </nav>
    {data.error && <ErrorBox error={data.error} onRetry={data.reload} />}
    {!result && !data.error && <TableSkeleton cols={3} rows={5} />}
    {result && !result.groups.length && <EmptyState icon={<Circle size={28} />} title="No SKU sets in this run" description="Open Documents to inspect the uploaded sources." action={<LinkButton to={`/runs/${enc(runId)}/documents`}>Open documents</LinkButton>} />}
    {result && !!result.groups.length && <>
      <div className="quick-toolbar">
        <div className="segmented" role="group" aria-label="Quick view mode">
          <button aria-pressed={view === "components"} onClick={() => change("view", "")}>Comparison</button>
          <button aria-pressed={view === "text"} onClick={() => change("view", "text")}>All extracted text</button>
        </div>
        <div className="quick-filters">
          {view === "components" && <label className="sr-only" htmlFor="quick-status">Comparison status</label>}
          {view === "components" && <select id="quick-status" className="input input-sm" value={status} onChange={e => change("status", e.target.value)}>
            <option value="compared">Compared entries</option><option value="all">All entries</option><option value="matched">Matched ({result.counts.matched || 0})</option><option value="attention">Missing or needs review ({result.counts.attention || 0})</option><option value="neutral">Not compared ({result.counts.neutral || 0})</option>
          </select>}
          <div className="relative"><MagnifyingGlass size={16} className="quick-search-icon" /><input className="input input-sm pl-8" aria-label="Search comparison text" placeholder="Find a word or item code" value={query} onChange={e => {setQuery(e.target.value); if (offset) change("offset", "");}} /></div>
        </div>
      </div>
      <div className="quick-context">
        <p><strong>{result.sku}</strong> · {result.total} {view === "text" ? "source rows" : "comparison rows"}{data.loading && " · Updating…"}</p>
        <div className="quick-legend"><Status status="matched" /><Status status="attention" /><Status status="neutral" /></div>
      </div>
      <p className="quick-hint">{view === "text" ? "Listed in source order; entries on the same row are not paired. Colours reflect the containing component’s comparison. Headers and notes are not compared." : "Green: accepted match with no unresolved finding. Orange: missing counterpart or review needed. Unmapped does not establish physical absence. This view does not approve results."}</p>
      {warnings > 0 && <details className="quick-warnings"><summary>{warnings} extraction warnings in this SKU</summary>{result.documents.filter(d => d.warnings.length).map(d => <div key={d.id}><strong>{d.file_name}</strong><ul>{d.warnings.map((w,n) => <li key={n}>{w}</li>)}</ul></div>)}</details>}
      {view === "text" && result.documents.some(d => !d.full_text) && <p className="quick-hint">{result.documents.filter(d => !d.full_text).map(d => d.file_name).join(", ")}: showing parsed entries because full-page text was not retained in this saved run.</p>}
      <div ref={matrix} className="quick-matrix-wrap" aria-busy={data.loading}>
        <table className="quick-matrix"><caption className="sr-only">{view === "text" ? "Extracted source text in independent source order" : "Three-document comparison"} for {activeSku}</caption>
          <thead><tr><th scope="col" className="quick-index">{view === "text" ? "Line" : "Status"}</th>{KINDS.map(k => <th key={k} scope="col"><span>{NAME[k]}</span><small>{result.documents.filter(d => d.doc_type === k).length} source document{result.documents.filter(d => d.doc_type === k).length === 1 ? "" : "s"}</small></th>)}</tr></thead>
          <tbody>{data.loading && <tr><td colSpan={4} className="quick-loading" role="status">Loading entries…</td></tr>}{!data.loading && !data.error && result.rows.map((row, n) => <tr key={row.id} className={selected?.id === row.id ? "is-selected" : ""}>
            <td className="quick-index"><button className="quick-select-row" onClick={() => choose(row)} aria-label={`Show sources for row ${offset + n + 1}`} aria-pressed={selected?.id === row.id}>{view === "components" ? <Status status={row.status} /> : offset + n + 1}</button></td>
            {KINDS.map(k => <td key={k}>{row.cells[k] ? <div>{row.cells[k]!.items.map((i, itemIndex) => <button key={i.id} className={`quick-entry quick-${row.cells[k]!.status}`} onClick={() => choose(row,k,i.id)} aria-label={`Show ${NAME[k]} source for row ${offset + n + 1}${row.cells[k]!.items.length > 1 ? `, entry ${itemIndex+1}` : ""}`} aria-pressed={selected?.id === row.id && (!focusItems[k] || focusItems[k] === i.id)}>
              <span className="quick-item">{i.item_number && <span className="quick-code">{i.item_number}</span>}<span className="quick-description">{i.description}</span>{view === "components" && !!i.attributes.es_text && <span className="quick-translation">{String(i.attributes.es_text)}</span>}
                <span className="quick-entry-meta">{i.quantity !== null && `${fmtQty(i.quantity)} ${i.uom || ""} · `}{i.file_name}{i.page && ` · p${i.page}`}</span>
              </span></button>)}</div> : <button className={`quick-empty-cell ${row.status === "neutral" ? "is-neutral" : ""}`} onClick={() => choose(row)} aria-label={`Show missing ${NAME[k]} for row ${offset + n + 1}`}><span>{!result.documents.some(d => d.doc_type === k) ? "Document unavailable" : row.status === "neutral" ? "Not compared" : "No counterpart in this row"}</span></button>}</td>)}
          </tr>)}</tbody>
        </table>
        {!data.loading && !data.error && !result.rows.length && <EmptyState icon={<MagnifyingGlass size={28} />} title="No entries match" description="Try a different status or search phrase." action={<Button onClick={() => {setQuery(""); setSearch(""); setParams(sku ? {sku,status:'all'} : {status:'all'});}}>Clear filters</Button>} />}
      </div>
      <Pagination offset={offset} size={100} total={result.total} onChange={n => change("offset", String(n))} label="Quick view" loading={data.loading} />
      <section ref={preview} className="quick-evidence" aria-label="Three source documents">
        <div className="quick-evidence-title"><div><h2>Source documents</h2><p>{selected ? "Selected text is highlighted in each available source. Page controls are independent." : "Select an entry above to highlight its locations across the documents."}</p></div><div className="flex gap-2 flex-wrap">{selected && <><Button size="sm" onClick={() => matrix.current?.scrollIntoView?.({block:"start"})}>Back to comparison</Button><Button size="sm" variant="ghost" onClick={() => setSelected(null)}>Clear selection</Button></>}</div></div>
        <QuickDocumentWorkspace key={`${runId}:${activeSku}`} runId={runId} sku={activeSku} documents={result.documents} selected={selected} preferred={focusItems} expanded={expanded} onExpanded={setExpanded} navigation={entryNavigation} details={comparisonDetails}/>

      </section>
    </>}
  </div>;
}

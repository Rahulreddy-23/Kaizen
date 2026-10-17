import { ArrowsClockwise, ArrowsOut, ArrowSquareOut, CheckCircle, Circle, MagnifyingGlass, WarningCircle } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox } from "../components/Feedback";
import { PageImage } from "../components/PageImage";
import { Pagination } from "../components/Pagination";
import { Button, Dialog, EmptyState, LinkButton, PageHeader, TableSkeleton } from "../components/ui";
import { enc, fmtQty, issueLabel } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useDataRefresh } from "../lib/dataRefresh";
import type { QuickCell, QuickDocument, QuickKind, QuickRow, QuickStatus, QuickView } from "../types";

const KINDS: QuickKind[] = ["BOM", "LABEL", "DRAWING"];
const NAME = {BOM: "BOM", LABEL: "Label", DRAWING: "Diagram"};
const STATUS = {matched: "Matched", attention: "Missing or needs review", neutral: "Not compared"};
const PAIR: Record<string, string> = {BOM_LABEL: "BOM ↔ Label", BOM_DRAWING: "BOM ↔ Diagram", LABEL_DRAWING: "Label ↔ Diagram"};

function Status({status}: {status: QuickStatus}) {
  const Icon = status === "matched" ? CheckCircle : status === "attention" ? WarningCircle : Circle;
  return <span className={`quick-status quick-${status}`}><Icon size={14} aria-hidden />{STATUS[status]}</span>;
}

function SourcePreview({runId, kind, documents, cell, missing, selected, preferred}: {
  runId: string; kind: QuickKind; documents: QuickDocument[]; cell: QuickCell | null; missing: boolean; selected: boolean; preferred?: string;
}) {
  const [choice, setChoice] = useState("");
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState("125");
  const document = documents.find(d => d.id === choice) ?? documents[0];
  const target = cell?.items.find(i => i.id === preferred) ?? cell?.items[0];
  const item = target && document && target.doc_id === document.id && target.page === page ? target : cell?.items.find(i => i.doc_id === document?.id && i.page === page) ?? cell?.items.find(i => i.doc_id === document?.id);
  const targetId = target?.doc_id;
  const targetPage = target?.page;
  useEffect(() => { if (targetId) {setChoice(targetId); setPage(targetPage ?? 1);} }, [targetId, targetPage, target?.id]);
  const actualPage = Math.min(Math.max(1, page), document?.pages || 1);
  const image = document?.pages ? api.pageImageUrl(runId, document.id, actualPage, null, 180) : null;
  const box = selected && item?.page === actualPage ? item.bbox : null;
  return <section className="quick-source" aria-label={`${NAME[kind]} source preview`}>
    <header className="quick-source-head"><h3>{NAME[kind]}</h3>{selected && cell && <Status status={cell.status} />}</header>
    {document ? <>
      <label className="sr-only" htmlFor={`quick-doc-${kind}`}>{NAME[kind]} document</label>
      <select id={`quick-doc-${kind}`} className="input input-sm w-full" value={document.id} onChange={e => {setChoice(e.target.value); setPage(1);}}>
        {documents.map(d => <option key={d.id} value={d.id}>{d.file_name}</option>)}
      </select>
      <div className="quick-page-controls">
        <label>Page <select className="input input-sm" aria-label={`${NAME[kind]} page`} value={actualPage} disabled={!document.pages} onChange={e => setPage(Number(e.target.value))}>
          {Array.from({length: document.pages || 1}, (_, n) => <option key={n} value={n + 1}>{n + 1} of {document.pages || 1}</option>)}
        </select></label>
        {document.pages > 0 && <label>Zoom <select className="input input-sm" aria-label={`${NAME[kind]} zoom`} value={zoom} onChange={e => setZoom(e.target.value)}>
          <option value="fit">Fit width</option>{[50,75,100,125,150,200].map(n => <option key={n} value={n}>{n}%</option>)}
        </select></label>}
        <Link className="quick-open" to={`/runs/${enc(runId)}/documents/${enc(document.id)}?page=${actualPage}`} aria-label={`Open ${NAME[kind]} document`}><ArrowSquareOut size={16} />Open</Link>
      </div>
      {missing && <p className="quick-gap">No counterpart in this comparison. There is no location to highlight.</p>}
      {selected && item && <p className="quick-locator">{item.locator || item.file_name}{item.page && ` · page ${item.page}`}{item.page !== actualPage && " · highlight is on another page"}</p>}
      <div className="quick-page-surface"><PageImage src={image} bbox={box} tone={cell?.status ?? "neutral"} alt={`${document.file_name}, page ${actualPage}`} fit={zoom === "fit"} zoom={zoom === "fit" ? undefined : Number(zoom)} dpi={180} maxHeight="var(--quick-preview-height, 72vh)"
        fallback={<p>{document.file_name.toLowerCase().endsWith('.pdf') ? "The page preview could not be loaded. Open the document to check the source." : "Spreadsheet source: use the extracted text and sheet/row locator below."}</p>} /></div>
      {selected && item && <details className="quick-raw"><summary>Selected source text</summary><p>{item.description}</p><pre>{item.raw_text}</pre></details>}
    </> : <div className="quick-unavailable"><WarningCircle size={24} /><strong>No {NAME[kind].toLowerCase()} document</strong><p>This SKU has no associated {NAME[kind].toLowerCase()} source.</p></div>}
  </section>;
}

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
  const sourcePanels = result && <div className="quick-sources">{KINDS.map(k => <SourcePreview key={`${runId}:${activeSku}:${k}`} runId={runId} kind={k} documents={result.documents.filter(d => d.doc_type === k)} cell={selected?.cells[k] ?? null} preferred={focusItems[k]} selected={!!selected} missing={!!selected && !selected.cells[k] && selected.status !== "neutral"} />)}</div>;
  return <div className="quick-view">
    <PageHeader back={{to:`/runs/${enc(runId)}`,label:"Overview"}} title="Quick view"
      description="Compare one SKU across its BOM, label and diagram. Select an entry to locate the source text."
      actions={<Button icon={<ArrowsClockwise size={16} />} onClick={data.reload} loading={data.loading}>Refresh</Button>} />
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
        <div className="quick-evidence-title"><div><h2>Source documents</h2><p>{selected ? "Selected text is highlighted in each available source. Page controls are independent." : "Select an entry above to highlight its locations across the documents."}</p></div><div className="flex gap-2 flex-wrap"><Button size="sm" icon={<ArrowsOut size={16} />} onClick={() => setExpanded(true)}>Expand documents</Button>{selected && <><Button size="sm" onClick={() => matrix.current?.scrollIntoView?.({block:"start"})}>Back to comparison</Button><Button size="sm" variant="ghost" onClick={() => setSelected(null)}>Clear selection</Button></>}</div></div>
        {!expanded && <div className="quick-document-workspace">{entryNavigation}{comparisonDetails}{sourcePanels}</div>}
        <Dialog open={expanded} onClose={() => setExpanded(false)} title="Source documents" description={`${activeSku} · Independent page and zoom controls. Press Escape to return.`} width="lg" className="quick-document-dialog" closeLabel="Close expanded documents">
          <div className="quick-document-workspace">{entryNavigation}{comparisonDetails}{sourcePanels}</div>
        </Dialog>
      </section>
    </>}
  </div>;
}

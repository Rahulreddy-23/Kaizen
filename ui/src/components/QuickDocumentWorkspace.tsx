import {ArrowsOut, ArrowSquareOut, CrosshairSimple, WarningCircle} from "@phosphor-icons/react";
import {Fragment, useEffect, useRef, useState, type ReactNode} from "react";
import {Link} from "react-router-dom";
import {api} from "../api";
import {enc} from "../lib/format";
import type {QuickCell, QuickDocument, QuickKind, QuickRow} from "../types";
import {PageImage} from "./PageImage";
import {QUICK_KINDS as KINDS, QUICK_NAME as NAME, QuickStatusLabel as Status} from "./QuickStatus";
import {Button, Dialog} from "./ui";

type PaneView = {documentId: string; page: number; zoom: string; locate: number};
type Weights = Record<QuickKind, number>;
type Layout = "three" | "two" | "focus";
const INITIAL_WEIGHTS: Weights = {BOM: 1, LABEL: 1, DRAWING: 1};
const initialView = (kind: QuickKind): PaneView => ({documentId: "", page: 1, zoom: kind === "BOM" ? "200" : "125", locate: 0});
const PAIRS: QuickKind[][] = [["BOM","LABEL"], ["BOM","DRAWING"], ["LABEL","DRAWING"]];

function Splitter({left, right, weights, totalWeight, onChange}: {left: QuickKind; right: QuickKind; weights: Weights; totalWeight: number; onChange: (next: Weights) => void}) {
  const drag = useRef<{x: number; width: number; total: number; weights: Weights} | null>(null);
  const sum = weights[left] + weights[right];
  const value = Math.round(weights[left] / sum * 100);
  const setShare = (share: number, base = weights) => {
    const pair = base[left] + base[right];
    const fraction = Math.min(.75, Math.max(.25, share / 100));
    onChange({...base, [left]: pair * fraction, [right]: pair * (1 - fraction)});
  };
  return <div className="quick-splitter" role="separator" tabIndex={0} aria-label={`Resize ${NAME[left]} and ${NAME[right]} panes`} aria-orientation="vertical" aria-valuemin={25} aria-valuemax={75} aria-valuenow={value} aria-controls={`reader-${left} reader-${right}`}
    onDoubleClick={() => setShare(50)}
    onKeyDown={e => {
      const next = e.key === "ArrowLeft" ? value - 5 : e.key === "ArrowRight" ? value + 5 : e.key === "Home" ? 25 : e.key === "End" ? 75 : e.key === "Enter" ? 50 : null;
      if (next !== null) {e.preventDefault(); setShare(next);}
    }}
    onPointerDown={e => {
      if (e.button !== 0) return;
      drag.current = {x:e.clientX,width:e.currentTarget.parentElement?.clientWidth || 1,total:totalWeight,weights:{...weights}};
      e.currentTarget.setPointerCapture?.(e.pointerId); e.preventDefault();
    }}
    onPointerMove={e => {
      const start = drag.current; if (!start) return;
      const pair = start.weights[left] + start.weights[right];
      setShare((start.weights[left] + (e.clientX-start.x) / start.width * start.total) / pair * 100,start.weights);
    }}
    onPointerUp={() => {drag.current = null;}} onPointerCancel={() => {drag.current = null;}}>
    <span aria-hidden />
  </div>;
}

function SourcePane({runId, kind, documents, cell, selected, missing, preferred, view, onView, onFocus, hidden}: {
  runId: string; kind: QuickKind; documents: QuickDocument[]; cell: QuickCell | null; selected: boolean; preferred?: string;
  view: PaneView; onView: (patch: Partial<PaneView>) => void; onFocus: () => void; hidden: boolean; missing: boolean;
}) {
  const doc = documents.find(d => d.id === view.documentId) ?? documents[0];
  const target = cell?.items.find(i => i.id === preferred) ?? cell?.items[0];
  const page = Math.min(Math.max(1,view.page),doc?.pages || 1);
  const item = target && target.doc_id === doc?.id && target.page === page ? target : cell?.items.find(i=>i.doc_id === doc?.id && i.page === page) ?? cell?.items.find(i=>i.doc_id === doc?.id);
  const box = selected && item?.page === page ? item.bbox : null;
  // Keep the rendered image stable throughout a pinch; reading scale is separate.
  const dpi = 300;
  const image = doc?.pages ? api.pageImageUrl(runId,doc.id,page,null,dpi) : null;
  const locate = () => {if (target) onView({documentId:target.doc_id,page:target.page ?? 1,locate:view.locate + 1});};
  return <section id={`reader-${kind}`} className="quick-reader-pane" aria-label={`${NAME[kind]} source preview`} hidden={hidden}>
    <header className="quick-pane-title"><div><h3>{NAME[kind]}</h3>{documents.length === 1 && <p title={doc?.file_name}>{doc?.file_name}</p>}</div>{selected && cell && <Status status={cell.status} />}<Button size="sm" variant="ghost" iconOnly icon={<ArrowsOut size={15}/>} aria-label={`Focus ${NAME[kind]}`} title={`Focus ${NAME[kind]}`} onClick={onFocus}/></header>
    {doc ? <>
      {documents.length > 1 && <><label className="sr-only" htmlFor={`reader-doc-${kind}`}>{NAME[kind]} document</label>
      <select id={`reader-doc-${kind}`} className="input input-sm quick-pane-file" title={doc.file_name} value={doc.id} onChange={e=>onView({documentId:e.target.value,page:1})}>{documents.map(d=><option key={d.id} value={d.id}>{d.file_name}</option>)}</select></>}
      <div className="quick-pane-tools">
        <label>Page <select className="input input-sm" aria-label={`${NAME[kind]} page`} value={page} disabled={!doc.pages} onChange={e=>onView({page:Number(e.target.value)})}>{Array.from({length:doc.pages || 1},(_,n)=><option key={n} value={n+1}>{n+1} / {doc.pages || 1}</option>)}</select></label>
        <label className="sr-only" htmlFor={`reader-zoom-${kind}`}>{NAME[kind]} zoom</label>
        <select id={`reader-zoom-${kind}`} className="input input-sm" value={view.zoom} disabled={!doc.pages} onChange={e=>onView({zoom:e.target.value})}><option value="fit">Fit width</option>{Array.from(new Set([25,50,75,100,125,150,200,300,400,...(view.zoom === "fit" ? [] : [Number(view.zoom)])])).sort((a,b)=>a-b).map(n=><option key={n} value={n}>{n}%</option>)}</select>
        <Button size="sm" variant="ghost" iconOnly icon={<CrosshairSimple size={16}/>} aria-label={`Locate selected text in ${NAME[kind]}`} disabled={!selected || !target?.page} onClick={locate}/>
        <Link className="quick-pane-open" to={`/runs/${enc(runId)}/documents/${enc(doc.id)}?page=${page}`} aria-label={`Open ${NAME[kind]} document`} title="Open full document"><ArrowSquareOut size={17}/></Link>
      </div>
      <div className={`quick-source-excerpt quick-${cell?.status ?? (missing ? "attention" : "neutral")}`}>
        {selected ? item ? <><strong>{item.description}</strong><small>{item.locator || item.file_name}{item.page !== page && " · Highlight on another page"}</small></> : <span>{cell ? "The selected entry is in another source file." : "No counterpart in this comparison. There is no location to highlight."}</span> : <span>Select a comparison entry to locate its source text.</span>}
      </div>
      <div className="quick-page-surface"><PageImage src={image} bbox={box} dpi={dpi} fit={view.zoom === "fit"} zoom={view.zoom === "fit" ? undefined : Number(view.zoom)} onZoomChange={percent=>onView({zoom:String(percent)})} focusToken={view.locate} pan alignWideEvidence="start" tone={cell?.status ?? "neutral"} alt={`${doc.file_name}, page ${page}`} maxHeight="100%"
        fallback={<p>{doc.file_name.toLowerCase().endsWith('.pdf') ? "Page preview unavailable. Open the document to inspect the source." : "Spreadsheet source: the selected text and sheet/row locator are shown above."}</p>}/></div>
      {selected && item && <details className="quick-pane-raw"><summary>Original source text</summary><pre>{item.raw_text}</pre></details>}
    </> : <div className="quick-unavailable"><WarningCircle size={24}/><strong>No {NAME[kind].toLowerCase()} document</strong><p>This SKU has no associated {NAME[kind].toLowerCase()} source.</p></div>}
  </section>;
}

export function QuickDocumentWorkspace({runId, sku, documents, selected, preferred, expanded, onExpanded, navigation, details}: {
  runId: string; sku: string; documents: QuickDocument[]; selected: QuickRow | null; preferred: Partial<Record<QuickKind,string>>;
  expanded: boolean; onExpanded: (value:boolean)=>void; navigation: ReactNode; details: ReactNode;
}) {
  const [layout,setLayout] = useState<Layout>("three");
  const [pair,setPair] = useState(0);
  const [focus,setFocus] = useState<QuickKind>("BOM");
  const [restore,setRestore] = useState<Layout>("three");
  const [weights,setWeights] = useState<Weights>(INITIAL_WEIGHTS);
  const [views,setViews] = useState<Record<QuickKind,PaneView>>({BOM:initialView("BOM"),LABEL:initialView("LABEL"),DRAWING:initialView("DRAWING")});
  const [narrow,setNarrow] = useState(false);
  const grid = useRef<HTMLDivElement>(null);
  useEffect(()=>{
    if (!selected) return;
    setViews(old=>Object.fromEntries(KINDS.map(k=>{
      const item=selected.cells[k]?.items.find(i=>i.id === preferred[k]) ?? selected.cells[k]?.items[0];
      return [k,item ? {...old[k],documentId:item.doc_id,page:item.page ?? 1,locate:old[k].locate+1} : old[k]];
    })) as Record<QuickKind,PaneView>);
  },[selected,preferred]);
  useEffect(()=>{
    const el=grid.current; if (!el || typeof ResizeObserver === "undefined") return;
    const update=()=>setNarrow(el.clientWidth < 700);
    update(); const observer=new ResizeObserver(update);observer.observe(el);return()=>observer.disconnect();
  },[expanded]);
  const visible = narrow || layout === "focus" ? [focus] : layout === "two" ? PAIRS[pair] : KINDS;
  const focusPane=(kind:QuickKind)=>{if(layout !== "focus")setRestore(layout);setFocus(kind);setLayout("focus");onExpanded(true);};
  const changeLayout=(next:Layout)=>{
    if (next === "focus" && layout !== "focus") {
      setRestore(layout);
      if (!visible.includes(focus)) setFocus(visible[0]);
    }
    setLayout(next);
    if (next !== "focus" && layout !== "focus") setWeights({...INITIAL_WEIGHTS});
  };
  const locateAll=()=>setViews(old=>Object.fromEntries(KINDS.map(k=>{
    const item=selected?.cells[k]?.items.find(i=>i.id === preferred[k]) ?? selected?.cells[k]?.items[0];
    return [k,{...old[k],...(item?{documentId:item.doc_id,page:item.page ?? 1}:{}),locate:old[k].locate+1}];
  })) as Record<QuickKind,PaneView>);
  const controls=<div className="quick-reader-toolbar">
    {!narrow && <div className="quick-reader-layout" role="group" aria-label="Document layout">
      <button aria-pressed={layout === "three"} onClick={()=>changeLayout("three")}>Three documents</button>
      <button aria-pressed={layout === "two"} onClick={()=>changeLayout("two")}>Two documents</button>
      <button aria-pressed={layout === "focus"} onClick={()=>changeLayout("focus")}>Focus</button>
    </div>}
    {layout === "two" && !narrow && <select className="input input-sm" aria-label="Document pair" value={pair} onChange={e=>setPair(Number(e.target.value))}>{PAIRS.map((p,n)=><option key={n} value={n}>{p.map(k=>NAME[k]).join(" + ")}</option>)}</select>}
    {(layout === "focus" || narrow) && <div className="quick-reader-tabs" role="group" aria-label="Focused source">{KINDS.map(k=><button key={k} aria-pressed={focus === k} onClick={()=>setFocus(k)}>{NAME[k]}</button>)}</div>}
    {!narrow && layout === "focus" && <Button size="sm" variant="ghost" onClick={()=>changeLayout(restore)}>Restore split view</Button>}
    <div className="quick-reader-utilities"><Button size="sm" variant="ghost" icon={<CrosshairSimple size={16}/>} disabled={!selected} onClick={locateAll}>Locate selected</Button>{!narrow && layout !== "focus" && <Button size="sm" variant="ghost" onClick={()=>setWeights({...INITIAL_WEIGHTS})}>Reset widths</Button>}</div>
    {details && <div className="quick-reader-check-menu">{details}</div>}
  </div>;
  const content=<div className="quick-reader-content">
    {controls}{navigation}
    <div ref={grid} className="quick-reader-grid" style={{gridTemplateColumns:visible.map((k,n)=>`minmax(0,${weights[k]}fr)${n < visible.length-1 ? " 10px" : ""}`).join(" ")}}>
      {KINDS.map(k=><Fragment key={k}>
        <SourcePane runId={runId} kind={k} documents={documents.filter(d=>d.doc_type === k)} cell={selected?.cells[k] ?? null} selected={!!selected} missing={!!selected && !selected.cells[k] && selected.status !== "neutral"} preferred={preferred[k]} view={views[k]} onView={patch=>setViews(old=>({...old,[k]:{...old[k],...patch}}))} onFocus={()=>focusPane(k)} hidden={!visible.includes(k)}/>
        {visible.includes(k) && visible.indexOf(k)<visible.length-1 && <Splitter left={k} right={visible[visible.indexOf(k)+1]} weights={weights} totalWeight={visible.reduce((sum,k)=>sum+weights[k],0)} onChange={setWeights}/>}
      </Fragment>)}
    </div>
    <p className="quick-reader-help">{narrow ? "Switch source tabs for full width. " : "Drag a divider to resize. "}Drag to pan. Spread two fingers to zoom in; pinch together to zoom out. Trackpad pinch or Ctrl + scroll also zooms.</p>
  </div>;
  return <>
    <div className="quick-reader-launch"><Button icon={<ArrowsOut size={16}/>} onClick={()=>onExpanded(true)}>Open document reader</Button><span>Adjustable splits · source-linked highlights</span></div>
    {!expanded && content}
    <Dialog open={expanded} onClose={()=>onExpanded(false)} title="Source documents" description={sku} width="lg" className="quick-document-dialog quick-reader-dialog" closeLabel="Close expanded documents">{content}</Dialog>
  </>;
}

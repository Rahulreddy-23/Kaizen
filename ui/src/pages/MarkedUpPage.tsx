import { ArrowsClockwise, Circle, FileArrowDown, FileZip } from "@phosphor-icons/react";
import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox } from "../components/Feedback";
import { QuickDocumentWorkspace } from "../components/QuickDocumentWorkspace";
import { QUICK_NAME as NAME } from "../components/QuickStatus";
import { AnchorButton, Button, EmptyState, LinkButton, PageHeader, TableSkeleton } from "../components/ui";
import { enc, fmtDayMonthYear } from "../lib/format";
import { useDataRefresh } from "../lib/dataRefresh";
import { useAsync } from "../lib/useAsync";

// Mirrors DOC_COLORS in kaizen/reporting/annotated.py. A mark wears the colour of the document it was
// compared against, so one key reads correctly on all three panes.
const KEY: { label: string; colour: string }[] = [
  { label: "Agrees with the BOM", colour: "#0D59E6" },
  { label: "Agrees with the label", colour: "#0D8C26" },
  { label: "Agrees with the PKG drawing", colour: "#8C1ABF" },
  { label: "Agrees with the PCO", colour: "#F2800D" },
];

export default function MarkedUpPage() {
  const { runId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const sku = params.get("sku") || "";
  const [expanded, setExpanded] = useState(false);
  const data = useAsync(() => api.quickView(runId, { sku, status: "all" }), [runId, sku]);
  const run = useAsync(() => api.getRun(runId), [runId]);
  useDataRefresh(data.refresh, runId);

  const result = data.data;
  const groups = result?.groups ?? [];
  const activeSku = result?.sku || sku;
  const documents = result?.documents ?? [];
  const choose = (next: string) => {
    const params = new URLSearchParams();
    if (next) params.set("sku", next);
    setParams(params);
  };

  return <div className="quick-view">
    <PageHeader back={{ to: `/runs/${enc(runId)}/quick-view${activeSku ? `?sku=${enc(activeSku)}` : ""}`, label: "Quick view" }}
      title="Marked-up documents"
      description="The three documents as they stand after review, each carrying the check marks its approvals have earned."
      actions={<>
        {!!documents.length && <AnchorButton href={api.annotatedBundleUrl(runId, activeSku)} download icon={<FileZip size={16} />}>
          Download all {documents.length}
        </AnchorButton>}
        <Button icon={<ArrowsClockwise size={16} />} onClick={data.reload} loading={data.loading}>Refresh</Button>
      </>} />

    <nav className="quick-skus" aria-label="SKU selection">
      {groups.map((g, n) => <button key={g.sku} className={`quick-sku ${activeSku === g.sku ? "is-active" : ""}`} aria-pressed={activeSku === g.sku} onClick={() => choose(g.sku)}>
        <strong>SKU {n + 1}</strong><span>{g.sku}</span>
      </button>)}
    </nav>

    {data.error && <ErrorBox error={data.error} onRetry={data.reload} />}
    {!result && !data.error && <TableSkeleton cols={3} rows={5} />}
    {result && !groups.length && <EmptyState icon={<Circle size={28} />} title="No SKU sets in this run"
      description="Open Documents to inspect the uploaded sources."
      action={<LinkButton to={`/runs/${enc(runId)}/documents`}>Open documents</LinkButton>} />}

    {result && !!groups.length && <>
      <div className="quick-context">
        {/* The same date the PDFs carry, chosen the same way: the newest decision, or the run itself
            when nobody has decided anything. A reader must not find two different answers. */}
        <p><strong>{result.sku}</strong> · {documents.length} documents · Updated {fmtDayMonthYear(run.data?.last_decided_at || run.data?.timestamp)}</p>
        <div className="quick-legend">
          {KEY.map(k => <span key={k.label} className="inline-flex items-center gap-1.5 text-xs">
            <span aria-hidden style={{ color: k.colour, fontWeight: 700 }}>✓</span>{k.label}
          </span>)}
        </div>
      </div>
      <p className="quick-hint">
        A tick means the comparison agreed and a cross means a discrepancy. Rows nobody has settled carry no mark,
        because a mark on these documents means one thing only: a reviewer decided this row.
        Marks follow the reviewers&rsquo; decisions, so the pages here and the files you download always say the same thing.
      </p>

      <div className="flex flex-wrap gap-1.5">
        {documents.map(d => <AnchorButton key={d.id} size="sm" href={api.annotatedUrl(runId, d.id)} download icon={<FileArrowDown size={16} />} title={d.file_name}>
          {NAME[d.doc_type]} PDF
        </AnchorButton>)}
      </div>

      <QuickDocumentWorkspace key={`${runId}:${activeSku}`} runId={runId} sku={activeSku} documents={documents}
        selected={null} preferred={{}} expanded={expanded} onExpanded={setExpanded} navigation={null} details={null} marks />
    </>}
  </div>;
}

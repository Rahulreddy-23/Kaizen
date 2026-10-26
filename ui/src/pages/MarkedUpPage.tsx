import { Circle, FileArrowDown, FileZip } from "@phosphor-icons/react";
import { useCallback, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox } from "../components/Feedback";
import { QuickDocumentWorkspace } from "../components/QuickDocumentWorkspace";
import { QUICK_NAME as NAME } from "../components/QuickStatus";
import { AnchorButton, EmptyState, LinkButton, PageHeader, TableSkeleton } from "../components/ui";
import { enc, fmtDayMonthYear } from "../lib/format";
import { useDataRefresh } from "../lib/dataRefresh";
import { useAsync } from "../lib/useAsync";

// Mirrors DOC_COLORS in kaizen/reporting/annotated.py. A mark wears the colour of the document it was
// compared against, so one key reads correctly on all three panes. Colour answers "against what?" and
// shape answers "with what result?", so each row shows both marks rather than only the tick.
const KEY: { label: string; colour: string }[] = [
  { label: "Checked against the BOM", colour: "#0D59E6" },
  { label: "Checked against the label", colour: "#0D8C26" },
  { label: "Checked against the PKG drawing", colour: "#8C1ABF" },
  { label: "Checked against the PCO", colour: "#F2800D" },
];

export default function MarkedUpPage() {
  const { runId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const sku = params.get("sku") || "";
  const [expanded, setExpanded] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const data = useAsync(() => api.quickView(runId, { sku, status: "all" }), [runId, sku]);
  const run = useAsync(() => api.getRun(runId), [runId]);
  const refresh = useCallback(() => {
    data.refresh();
    run.refresh();
    setRefreshVersion(version => version + 1);
  }, [data.refresh, run.refresh]);
  useDataRefresh(refresh, runId);
  const marksRevision = `${run.data?.last_decided_at || run.data?.timestamp || "initial"}:${refreshVersion}`;

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
      actions={!!documents.length && <AnchorButton href={api.annotatedBundleUrl(runId, activeSku)} download icon={<FileZip size={16} />}>
        Download all {documents.length}
      </AnchorButton>} />

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
      <div className="marked-intro">
        <div className="marked-intro-text">
          {/* The same date the PDFs carry, chosen the same way: the newest decision, or the run itself
              when nobody has decided anything. A reader must not find two different answers. */}
          <p className="marked-meta"><strong>{result.sku}</strong> · {documents.length} documents · Updated {fmtDayMonthYear(run.data?.last_decided_at || run.data?.timestamp)}</p>
          <p className="quick-hint">
            A tick means the check agreed and a cross means a discrepancy. Rows the comparison could not settle
            carry no mark until a reviewer decides them. A reviewer&rsquo;s decision always wins over the comparison,
            so the pages here and the files you download always say the same thing.
          </p>
        </div>
        <div className="marked-legend">
          <b>What the marks mean</b>
          {KEY.map(k => <span key={k.label}>
            <span aria-hidden style={{ color: k.colour, fontWeight: 700 }}>✓<i>✗</i></span>{k.label}
          </span>)}
          {/* Shape carries the result, and it is the same three answers whatever the colour. Saying it
              once here beats eight rows that repeat each document's name twice. */}
          <em>tick = agrees · cross = differs · no mark = needs a reviewer</em>
        </div>
      </div>

      <div className="marked-downloads">
        {documents.map(d => <AnchorButton key={d.id} size="sm" href={api.annotatedUrl(runId, d.id)} download icon={<FileArrowDown size={16} />} title={d.file_name}>
          {NAME[d.doc_type]} PDF
        </AnchorButton>)}
      </div>

      <QuickDocumentWorkspace key={`${runId}:${activeSku}`} runId={runId} sku={activeSku} documents={documents}
        selected={null} preferred={{}} expanded={expanded} onExpanded={setExpanded} navigation={null} details={null} marks marksRevision={marksRevision} />
    </>}
  </div>;
}

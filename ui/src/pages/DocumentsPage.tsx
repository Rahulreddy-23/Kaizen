import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { DocTypeBadge } from "../components/Badges";
import { ErrorBox, Loading } from "../components/Feedback";
import { enc, shortSha } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { DOC_TYPES } from "../types";

export default function DocumentsPage() {
  const { runId = "" } = useParams();
  const nav = useNavigate();
  const docs = useAsync(() => api.getDocuments(runId), [runId]);
  if (docs.error) return <ErrorBox error={docs.error} onRetry={docs.reload} />;
  if (!docs.data) return <Loading label="Loading documents…" />;
  const order = (t: string) => DOC_TYPES.indexOf(t as (typeof DOC_TYPES)[number]);
  const sorted = [...docs.data].sort((a, b) => (a.sku ?? "").localeCompare(b.sku ?? "") || order(a.doc_type) - order(b.doc_type) || a.file_name.localeCompare(b.file_name));
  const warnings = docs.data.reduce((n, d) => n + d.warnings.length, 0);
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-3 flex-wrap">
        <h1>Documents</h1>
        <span className="text-xs text-gray-500">
          {docs.data.length} parsed documents · {warnings} parser warning{warnings === 1 ? "" : "s"}. Open a document to verify the extraction against the page.
        </span>
      </div>
      <div className="panel overflow-x-auto">
        <table className="tbl">
          <thead>
            <tr>
              <th>Type</th>
              <th>File</th>
              <th>SKU</th>
              <th>Parser</th>
              <th className="text-right">Items</th>
              <th className="text-right">Pages</th>
              <th>Warnings</th>
              <th>SHA-256</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((d) => (
              <tr key={d.id} className="clickable" onClick={() => nav(`/runs/${enc(runId)}/documents/${enc(d.id)}`)}>
                <td>
                  <DocTypeBadge value={d.doc_type} />
                </td>
                <td className="mono">
                  <Link className="underline" to={`/runs/${enc(runId)}/documents/${enc(d.id)}`}>
                    {d.file_name}
                  </Link>
                  <div className="text-2xs text-gray-400 break-all">{d.file}</div>
                </td>
                <td className="mono">{d.sku ?? <span className="text-gray-400">—</span>}</td>
                <td className="whitespace-nowrap">
                  {d.parser} <span className="text-gray-500">v{d.parser_version}</span>
                </td>
                <td className="text-right tabular-nums">{d.items}</td>
                <td className="text-right tabular-nums">{d.pages || <span className="text-gray-400">xlsx</span>}</td>
                <td className={d.warnings.length ? "text-amber-800" : "text-gray-400"}>{d.warnings.length ? d.warnings.join("; ") : "—"}</td>
                <td className="mono text-gray-500" title={d.sha256}>
                  {shortSha(d.sha256)}
                </td>
                <td className="whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                  {d.doc_type === "BOM" && (
                    <a className="btn btn-sm" href={api.annotatedBomUrl(runId, d.id)} download title="BOM PDF with check marks from the reviewer decisions">
                      Annotated BOM (PDF)
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

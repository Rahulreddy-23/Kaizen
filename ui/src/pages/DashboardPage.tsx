import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ClassificationBadge, SeverityBadge, StateBadge } from "../components/Badges";
import { ErrorBox, Loading } from "../components/Feedback";
import { Bar, CLASS_COLORS, Stat } from "../components/Stat";
import { enc, fmtBytes, fmtDate, shortSha } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { errorMessage, useAsync } from "../lib/useAsync";
import { CHECK_TYPES, CLASSIFICATIONS, DOC_TYPES, REVIEW_STATES, type Severity, type VerifyOutcome } from "../types";

const SEV_RANK: Record<Severity, number> = { BLOCKER: 0, MAJOR: 1, MINOR: 2, INFO: 3 };

export default function DashboardPage() {
  const { runId = "" } = useParams();
  const { viewerParams } = useReviewer();
  const run = useAsync(() => api.getRun(runId), [runId]);
  // Rows needing validation, to list unresolved discrepancies by type (cheap: a few hundred rows).
  const nv = useAsync(
    () => api.getResults(runId, { needs_validation: true, limit: 5000, viewer: viewerParams.viewer, blind: viewerParams.blind || undefined }),
    [runId, viewerParams.viewer, viewerParams.blind],
  );
  const [verify, setVerify] = useState<VerifyOutcome | null>(null);
  const [verifyErr, setVerifyErr] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  if (run.error) return <ErrorBox error={run.error} onRetry={run.reload} />;
  if (!run.data) return <Loading label="Loading run…" />;
  const r = run.data;
  const base = `/runs/${enc(runId)}`;
  const queue = (params: Record<string, string>) => `${base}/review?${new URLSearchParams(params).toString()}`;

  const rows = nv.data?.rows ?? [];
  const unresolved = rows.filter((x) => x.discrepancies.length > 0 && x.state !== "FINALIZED");
  const byType = new Map<string, { count: number; top: Severity }>();
  for (const x of unresolved) {
    for (const d of x.discrepancies) {
      const cur = byType.get(d.type);
      if (!cur) byType.set(d.type, { count: 1, top: d.severity });
      else {
        cur.count += 1;
        if (SEV_RANK[d.severity] < SEV_RANK[cur.top]) cur.top = d.severity;
      }
    }
  }
  const typeRows = [...byType.entries()].sort((a, b) => SEV_RANK[a[1].top] - SEV_RANK[b[1].top] || b[1].count - a[1].count);
  const coverageIssues = r.coverage.filter((c) => c.status !== "OK");
  const untouched = rows.filter((x) => x.state === "ENGINE_RECOMMENDED").length;
  const reviewable = r.reviewable_rows ?? r.rows;
  const headerNeeds = r.header_rows_needing_validation ?? 0;
  const disagreements = r.state_counts.DISAGREEMENT ?? 0;

  const doVerify = async () => {
    setVerifying(true);
    setVerifyErr(null);
    try {
      setVerify(await api.verifyAndClose(runId));
    } catch (e) {
      setVerifyErr(errorMessage(e));
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="mono">{r.run_id}</h1>
        <span className="text-xs text-gray-600">
          {fmtDate(r.timestamp)} · tool {r.tool_version} · terminology <span className="mono" title={r.terminology_version}>{shortSha(r.terminology_version)}</span> ({r.terminology_count} relationships)
        </span>
        <span className="mono text-xs text-gray-500 break-all">{r.input_root}</span>
        <div className="ml-auto flex gap-1 flex-wrap">
          <Link className="btn btn-primary" to={queue({})}>
            Review queue
          </Link>
          <Link className="btn" to={`${base}/documents`}>
            Documents
          </Link>
          <Link className="btn" to={`${base}/mining`}>
            Mining
          </Link>
          <Link className="btn" to={`${base}/business`}>
            Business case
          </Link>
          <Link className="btn" to="/terminology">
            Terminology
          </Link>
          <Link className="btn" to={`/action-items?run_id=${enc(runId)}`}>
            Action items
          </Link>
          <a className="btn" href={api.exportUrl(runId)} download>
            Export .xlsx
          </a>
          <a className="btn" href={api.certificateUrl(runId)} download title="One page per SKU: run id, file hashes, counts, named reviewers, open action items">
            Certificate .pdf
          </a>
          <Link className="btn" to={`/runs/${enc(runId)}/diff`} title="Resolved, new and still-open discrepancies against an earlier run">
            Compare with a run
          </Link>
          <button className="btn" onClick={doVerify} disabled={verifying} title="Match open action items from earlier runs against this run's results">
            {verifying ? "Verifying…" : "Verify & close against this run"}
          </button>
        </div>
      </div>

      {verifyErr && <ErrorBox error={verifyErr} />}
      {verify && (
        <div className="panel">
          <div className="panel-title">Verify & close — outcome</div>
          <div className="p-3 grid md:grid-cols-3 gap-3 text-xs">
            <div>
              <div className="label text-green-800">Resolved ({verify.resolved.length})</div>
              <div className="text-gray-600 mb-1">Discrepancy no longer present in this run; action item marked RESOLVED.</div>
              <List ids={verify.resolved} />
            </div>
            <div>
              <div className="label text-red-800">Still open ({verify.still_open.length})</div>
              <div className="text-gray-600 mb-1">The same comparison still shows the discrepancy.</div>
              <List ids={verify.still_open} />
            </div>
            <div>
              <div className="label">Not covered ({verify.not_covered.length})</div>
              <div className="text-gray-600 mb-1">This run has no comparison for the item (different SKU set).</div>
              <List ids={verify.not_covered} />
            </div>
          </div>
        </div>
      )}

      {/* ---- the headline: what needs attention */}
      <div className="panel">
        <div className="grid grid-cols-2 divide-x divide-gray-200">
          <div className="p-4">
            <div className="label">Auto-cleared by the engine</div>
            <div className="text-4xl font-semibold text-green-800 tabular-nums leading-none mt-1">{r.auto_cleared}</div>
            <div className="text-xs text-gray-600 mt-1">
              EXACT or EQUIVALENT with no discrepancy. Still recorded, still auditable —{" "}
              <Link className="underline" to={queue({ nv: "0", classification: "EXACT" })}>
                inspect
              </Link>
              .
            </div>
          </div>
          <div className="p-4">
            <div className="label">Needs human review</div>
            <div className="text-4xl font-semibold text-red-800 tabular-nums leading-none mt-1">{r.needs_validation}</div>
            <div className="text-xs text-gray-600 mt-1">
              of {reviewable} reviewable comparison{reviewable === 1 ? "" : "s"} · <b className={r.blockers ? "text-red-900" : ""}>{r.blockers}</b> blocker{r.blockers === 1 ? "" : "s"} ·{" "}
              {r.low_confidence_rows} low-confidence extraction{r.low_confidence_rows === 1 ? "" : "s"} · {nv.data ? `${untouched} untouched in the queue` : "…"}
              {disagreements > 0 && (
                <>
                  {" "}
                  · <b className="text-red-900">{disagreements} DISAGREEMENT{disagreements === 1 ? "" : "S"}</b>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="px-4 pb-3">
          <Bar
            segments={[
              { label: "Auto-cleared", value: r.auto_cleared, color: "#15803d" },
              { label: "Needs human review", value: r.needs_validation, color: "#b91c1c" },
            ]}
            height={14}
          />
          {(headerNeeds > 0 || (r.exempt_rows ?? 0) > 0) && (
            <div className="text-2xs text-gray-500 mt-1">
              Not counted above: {headerNeeds} header / reference / coverage row{headerNeeds === 1 ? "" : "s"} needing validation (they lead the queue){r.exempt_rows ? ` and ${r.exempt_rows} exempt rows (non-physical BOM lines, listed for traceability)` : ""}.
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-2">
        <Stat label="SKUs" value={r.skus} />
        <Stat label="Documents" value={r.documents} sub={DOC_TYPES.map((t) => `${t} ${r.documents_by_type[t] ?? 0}`).join(" · ")} />
        <Stat label="Unrecognised files" value={r.unrecognised_files.length} tone={r.unrecognised_files.length ? "warn" : "neutral"} />
        <Stat label="Comparisons" value={r.rows} sub={r.reviewable_rows !== undefined ? `${r.reviewable_rows} reviewable · ${r.exempt_rows ?? 0} exempt` : undefined} />
        <Stat label="Blockers" value={r.blockers} tone={r.blockers ? "bad" : "good"} />
        <Stat label="Low-confidence rows" value={r.low_confidence_rows} tone={r.low_confidence_rows ? "warn" : "neutral"} />
        <Stat label="Coverage issues" value={coverageIssues.length} tone={coverageIssues.length ? "bad" : "good"} />
      </div>

      <div className="grid xl:grid-cols-2 gap-3">
        {/* ---- why: unresolved discrepancies + coverage + warnings */}
        <div className="panel">
          <div className="panel-title">
            Unresolved discrepancies by type
            <span className="ml-auto normal-case font-normal text-gray-500">{nv.loading ? "counting…" : `${unresolved.length} rows not finalized`}</span>
          </div>
          {nv.error && (
            <div className="p-3">
              <ErrorBox error={nv.error} onRetry={nv.reload} />
            </div>
          )}
          {typeRows.length === 0 && !nv.loading && !nv.error && <div className="p-3 text-xs text-gray-500">No open discrepancies.</div>}
          {typeRows.length > 0 && (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Top severity</th>
                  <th>Discrepancy type</th>
                  <th className="text-right">Rows</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {typeRows.map(([t, v]) => (
                  <tr key={t}>
                    <td>
                      <SeverityBadge value={v.top} />
                    </td>
                    <td className="mono">{t}</td>
                    <td className="text-right tabular-nums">{v.count}</td>
                    <td>
                      <Link className="underline" to={queue({ discrepancy: t, nv: "0" })}>
                        open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {r.warnings.length > 0 && (
            <div className="border-t border-gray-200 p-3">
              <div className="label mb-1">Run warnings</div>
              <ul className="text-xs list-disc pl-4 space-y-0.5">
                {r.warnings.map((w, i) => (
                  <li key={i} className={/BLOCKER/.test(w) ? "text-red-900 font-semibold" : ""}>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div className="panel">
            <div className="panel-title">Engine classification of all {r.rows} comparisons</div>
            <div className="p-3">
              <Bar segments={CLASSIFICATIONS.map((c) => ({ label: c, value: r.counts[c] ?? 0, color: CLASS_COLORS[c] }))} />
              <div className="flex flex-wrap gap-1 mt-2">
                {CLASSIFICATIONS.map((c) => (
                  <Link key={c} className="btn btn-sm" to={queue({ classification: c, nv: "0" })}>
                    <ClassificationBadge value={c} /> {r.counts[c] ?? 0}
                  </Link>
                ))}
              </div>
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <div className="panel">
              <div className="panel-title">Per check</div>
              <table className="tbl">
                <tbody>
                  {CHECK_TYPES.map((c) => (
                    <tr key={c}>
                      <td className="mono">{c}</td>
                      <td className="text-right tabular-nums">{r.per_check[c] ?? 0}</td>
                      <td className="text-right">
                        <Link className="underline" to={queue({ check: c })}>
                          review
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="panel">
              <div className="panel-title">Review state</div>
              <table className="tbl">
                <tbody>
                  {REVIEW_STATES.map((s) => (
                    <tr key={s}>
                      <td>
                        <StateBadge value={s} />
                      </td>
                      <td className="text-right tabular-nums">{r.state_counts[s] ?? 0}</td>
                      <td className="text-right">
                        <Link className="underline" to={queue({ state: s, nv: "0" })}>
                          open
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="grid xl:grid-cols-2 gap-3">
        <div className="panel">
          <div className="panel-title">
            PCO coverage and SKU document sets
            <span className="ml-auto normal-case font-normal text-gray-500">{coverageIssues.length} issue{coverageIssues.length === 1 ? "" : "s"}</span>
          </div>
          <div className="max-h-80 overflow-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Kind</th>
                  <th>SKU</th>
                  <th>Detail</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {[...r.coverage]
                  .sort((a, b) => (a.status === "OK" ? 1 : 0) - (b.status === "OK" ? 1 : 0))
                  .map((c, i) => {
                    const bad = c.status.startsWith("MISSING");
                    return (
                      <tr key={i} className={bad ? "bg-red-50" : ""}>
                        <td>{bad ? <SeverityBadge value="BLOCKER" /> : <span className="text-green-800 font-semibold">{c.status}</span>}</td>
                        <td className="text-gray-600">{c.kind}</td>
                        <td className="mono">{c.sku}</td>
                        <td className={bad ? "text-red-900 font-medium" : ""}>
                          {bad && <span className="mono mr-1">{c.status}</span>}
                          {c.detail}
                        </td>
                        <td className="mono text-gray-500 break-all">{c.source}</td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel">
          <div className="panel-title">
            Parser warnings
            <span className="ml-auto normal-case font-normal text-gray-500">{r.parser_warnings.reduce((n, p) => n + p.warnings.length, 0)}</span>
          </div>
          {r.parser_warnings.length === 0 ? (
            <div className="p-3 text-xs text-gray-500">No parser warnings.</div>
          ) : (
            <div className="max-h-80 overflow-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Warning</th>
                  </tr>
                </thead>
                <tbody>
                  {r.parser_warnings.flatMap((p) =>
                    p.warnings.map((w, i) => (
                      <tr key={`${p.doc_id}-${i}`}>
                        <td className="mono whitespace-nowrap">
                          <Link className="underline" to={`${base}/documents/${enc(p.doc_id)}`}>
                            {p.document}
                          </Link>
                          <div className="text-gray-400 text-2xs">{p.doc_id}</div>
                        </td>
                        <td>{w}</td>
                      </tr>
                    )),
                  )}
                </tbody>
              </table>
            </div>
          )}
          {r.unrecognised_files.length > 0 && (
            <div className="border-t border-gray-200 p-3">
              <div className="label mb-1">Unrecognised files (ignored)</div>
              <ul className="mono text-xs">
                {r.unrecognised_files.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <details className="panel">
        <summary className="panel-title cursor-pointer select-none">Run record: SKU groups, relationships used, thresholds, capabilities, input hashes</summary>
        <div className="p-3 grid lg:grid-cols-2 gap-4 text-xs">
          <div>
            <div className="label mb-1">SKU groups ({r.groups.length})</div>
            <table className="tbl">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Family</th>
                  <th className="text-right">Docs</th>
                  <th>Warnings</th>
                </tr>
              </thead>
              <tbody>
                {r.groups.map((g) => (
                  <tr key={g.sku}>
                    <td className="mono">
                      <Link className="underline" to={queue({ sku: g.sku })}>
                        {g.sku}
                      </Link>
                    </td>
                    <td className="mono">{g.family}</td>
                    <td className="text-right tabular-nums">{g.document_ids.length}</td>
                    <td className="text-amber-800">{g.warnings.join("; ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="label mt-3 mb-1">Relationships used ({r.relationships_used.length})</div>
            <div className="flex flex-wrap gap-1">
              {r.relationships_used.map((id) => (
                <Link key={id} className="chip mono underline" to={`/terminology?id=${enc(id)}`}>
                  {id}
                </Link>
              ))}
              {r.relationships_used.length === 0 && <span className="text-gray-500">none</span>}
            </div>
            <div className="label mt-3 mb-1">Thresholds</div>
            <dl className="kv">
              {Object.entries(r.thresholds).map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="mono">{k}</dt>
                  <dd className="tabular-nums">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div>
            <div className="label mb-1">Capabilities</div>
            <table className="tbl">
              <tbody>
                {Object.entries(r.capabilities).map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td className={`whitespace-nowrap ${v === "IMPLEMENTED" ? "text-green-800" : "text-gray-500"}`}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="label mt-3 mb-1">Inputs ({r.inputs.length})</div>
            <div className="max-h-64 overflow-auto">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Path</th>
                    <th>Type</th>
                    <th className="text-right">Size</th>
                    <th>SHA-256</th>
                  </tr>
                </thead>
                <tbody>
                  {r.inputs.map((f) => (
                    <tr key={f.path}>
                      <td className="mono break-all">{f.path}</td>
                      <td>{f.doc_type ?? <span className="text-amber-800">unrecognised</span>}</td>
                      <td className="text-right tabular-nums whitespace-nowrap">{fmtBytes(f.size_bytes)}</td>
                      <td className="mono text-gray-500" title={f.sha256}>
                        {shortSha(f.sha256, 16)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </details>
    </div>
  );
}

function List({ ids }: { ids: string[] }) {
  if (ids.length === 0) return <div className="text-gray-400">—</div>;
  return (
    <ul className="mono space-y-0.5">
      {ids.map((id) => (
        <li key={id}>
          <Link className="underline" to={`/action-items?id=${enc(id)}`}>
            {id}
          </Link>
        </li>
      ))}
    </ul>
  );
}

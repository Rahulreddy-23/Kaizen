import { ArrowLeft, ArrowRight } from "@phosphor-icons/react";
import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ClassificationBadge, RoleTag, SeverityBadge } from "../components/Badges";
import { DecisionPanel } from "../components/DecisionPanel";
import { EvidenceCard } from "../components/EvidenceCard";
import { ErrorBox, Loading } from "../components/Feedback";
import { HotkeyHelp, HotkeyHint } from "../components/HotkeyHelp";
import { ActionItemPanel, SaveRelationshipPanel } from "../components/RowActions";
import { Button, Card, LinkButton, PageHeader } from "../components/ui";
import { enc, fmtScore } from "../lib/format";
import { useHotkeys } from "../lib/hotkeys";
import { PAGE_SIZE, queueParams, queueQueryFromParams } from "../lib/queue";
import { useReviewer } from "../lib/reviewer";
import { useAsync } from "../lib/useAsync";
import type { ViewerParams } from "../types";

const CHECK_LABEL: Record<string, string> = { BOM_LABEL: "BOM to label", BOM_DRAWING: "BOM to drawing", LABEL_DRAWING: "Label to drawing", PCO_BOM: "PCO to BOM", LABEL_REVISION: "Label revision" };

interface Neighbor {
  id: string;
  offset: number;
}
interface Neighbors {
  prev: Neighbor | null;
  next: Neighbor | null;
  index: number | null;
  total: number;
}

/** Prev/next within the queue's current filters (carried in the query string). */
function useNeighbors(runId: string, rowId: string, sp: URLSearchParams, v: ViewerParams) {
  return useAsync<Neighbors>(async () => {
    const q = queueQueryFromParams(sp, v);
    const offset = q.offset ?? 0;
    const page = await api.getResults(runId, q);
    const idx = page.rows.findIndex((r) => r.row_id === rowId);
    if (idx < 0) return { prev: null, next: null, index: null, total: page.total };
    let prev: Neighbor | null = idx > 0 ? { id: page.rows[idx - 1].row_id, offset } : null;
    let next: Neighbor | null = idx < page.rows.length - 1 ? { id: page.rows[idx + 1].row_id, offset } : null;
    if (!prev && offset > 0) {
      const p = await api.getResults(runId, { ...q, limit: 1, offset: offset - 1 });
      if (p.rows[0]) prev = { id: p.rows[0].row_id, offset: Math.max(0, offset - PAGE_SIZE) };
    }
    if (!next && offset + page.rows.length < page.total) {
      const p = await api.getResults(runId, { ...q, limit: 1, offset: offset + page.rows.length });
      if (p.rows[0]) next = { id: p.rows[0].row_id, offset: offset + PAGE_SIZE };
    }
    return { prev, next, index: offset + idx + 1, total: page.total };
  }, [runId, rowId, sp.toString(), v.viewer, v.blind]);
}

export default function EvidencePage() {
  const { runId = "", rowId = "" } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const { viewerParams } = useReviewer();
  const detail = useAsync(() => api.getRow(runId, rowId, viewerParams), [runId, rowId, viewerParams.viewer, viewerParams.blind]);
  const nb = useNeighbors(runId, rowId, sp, viewerParams);

  const qp = queueParams(sp);
  const rowLink = (n: Neighbor) => {
    const p = new URLSearchParams(qp);
    if (n.offset > 0) p.set("offset", String(n.offset));
    else p.delete("offset");
    return `/runs/${enc(runId)}/rows/${enc(n.id)}?${p.toString()}`;
  };
  const queueLink = `/runs/${enc(runId)}/review?${qp.toString()}`;

  // Keyboard: j/] next, k/[ previous, ? help, Esc back to the queue. Decision keys live in DecisionPanel.
  const [help, setHelp] = useState(false);
  const prev = () => nb.data?.prev && nav(rowLink(nb.data.prev));
  const next = () => nb.data?.next && nav(rowLink(nb.data.next));
  useHotkeys(
    { j: next, "]": next, k: prev, "[": prev, "?": () => setHelp((v) => !v), Escape: () => (help ? setHelp(false) : nav(queueLink)) },
    [nb.data, runId, help, queueLink],
  );

  if (detail.error) return <ErrorBox error={detail.error} onRetry={detail.reload} />;
  if (!detail.data) return <Loading label="Loading row" lines={6} />;
  const d = detail.data;
  const res = d.result;
  const topSeverity = res.discrepancies.length > 0 ? [...res.discrepancies].sort((a, b) => sevRank(a.severity) - sevRank(b.severity))[0].severity : null;

  return (
    <div>
      <HotkeyHelp open={help} onClose={() => setHelp(false)} />
      <PageHeader
        back={{ to: queueLink, label: "Queue" }}
        title={
          <>
            <span className="mono text-xl whitespace-nowrap">{res.row_id}</span>
            {topSeverity && <SeverityBadge value={topSeverity} size="md" />}
            <RoleTag value={res.role} />
          </>
        }
        meta={
          <>
            <span>
              SKU <span className="mono text-ink">{res.sku}</span>
            </span>
            <span>{CHECK_LABEL[res.check] ?? res.check}</span>
            {nb.data?.index !== null && nb.data && (
              <span className="num">
                {nb.data.index} of {nb.data.total} in the queue
              </span>
            )}
            {nb.data && nb.data.index === null && !nb.loading && <span>Not in the current queue filter</span>}
            <HotkeyHint />
          </>
        }
        actions={
          <>
            {nb.data?.prev ? (
              <LinkButton to={rowLink(nb.data.prev)} icon={<ArrowLeft size={16} />} title="Previous row (k)">
                Previous
              </LinkButton>
            ) : (
              <Button disabled icon={<ArrowLeft size={16} />}>
                Previous
              </Button>
            )}
            {nb.data?.next ? (
              <LinkButton to={rowLink(nb.data.next)} iconRight={<ArrowRight size={16} />} title="Next row (j)">
                Next
              </LinkButton>
            ) : (
              <Button disabled iconRight={<ArrowRight size={16} />}>
                Next
              </Button>
            )}
          </>
        }
      />

      <div className="space-y-5">
        {/* ---- the engine's recommendation and why */}
        <Card>
          <div className="grid gap-5 lg:grid-cols-[16rem_1fr] p-5">
            <div>
              <div className="text-xs font-medium text-ink-2">Engine recommendation</div>
              <div className="mt-1.5">
                <ClassificationBadge value={res.classification} size="lg" title="Engine recommendation, not a reviewer decision" />
              </div>
              <div className={`text-xs mt-2 font-medium ${res.requires_validation ? "text-bad-strong" : "text-ok-strong"}`}>{res.requires_validation ? "Requires human validation" : "Auto-cleared: no validation required"}</div>
              {d.effective_classification !== res.classification && (
                <div className="mt-3">
                  <div className="text-xs font-medium text-ink-2">After reviewer override</div>
                  <div className="mt-1">
                    <ClassificationBadge value={d.effective_classification} />
                  </div>
                </div>
              )}
              <dl className="kv mt-4 text-xs">
                <dt>Match level</dt>
                <dd className="mono">{res.match_level}</dd>
                <dt>Score</dt>
                <dd className="num">{fmtScore(res.score)}</dd>
                {res.relationship_id && (
                  <>
                    <dt>Relationship</dt>
                    <dd>
                      <Link className="mono" to={`/terminology?id=${enc(res.relationship_id)}`}>
                        {res.relationship_id}
                      </Link>
                    </dd>
                  </>
                )}
                {(res.normalized_a || res.normalized_b) && (
                  <>
                    <dt>Normalised A</dt>
                    <dd className="mono">{res.normalized_a ?? "—"}</dd>
                    <dt>Normalised B</dt>
                    <dd className="mono">{res.normalized_b ?? "—"}</dd>
                  </>
                )}
              </dl>
            </div>
            <div className="min-w-0">
              <div className="text-xs font-medium text-ink-2">Why</div>
              <p className="text-md font-medium text-ink mt-1 leading-6">{res.explanation}</p>
              {res.discrepancies.length > 0 ? (
                <div className="mt-4 -mx-5 -mb-5 border-t border-line">
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th>Severity</th>
                        <th>Discrepancy</th>
                        <th>Detail</th>
                        <th>Recommended action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {res.discrepancies.map((x, i) => (
                        <tr key={i}>
                          <td>
                            <SeverityBadge value={x.severity} />
                          </td>
                          <td className="mono whitespace-nowrap">{x.type}</td>
                          <td className="text-ink-2">{x.detail}</td>
                          <td className="text-ink">{x.recommended_action || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-sm text-ink-3 mt-2">No discrepancy recorded by the engine.</div>
              )}
            </div>
          </div>
        </Card>

        {/* ---- the evidence, side by side */}
        <div className="grid xl:grid-cols-2 gap-5">
          <EvidenceCard side="A" runId={runId} rowId={rowId} ev={d.evidence.a} itemId={res.source_a?.id} />
          <EvidenceCard side="B" runId={runId} rowId={rowId} ev={d.evidence.b} itemId={res.source_b?.id} />
        </div>

        {/* ---- decide, and what follows from it */}
        <div className="grid xl:grid-cols-[3fr_2fr] gap-5">
          <DecisionPanel runId={runId} rowId={rowId} detail={d} onChanged={detail.reload} />
          <div className="space-y-5">
            <SaveRelationshipPanel runId={runId} detail={d} onCreated={detail.reload} />
            <ActionItemPanel runId={runId} detail={d} onCreated={detail.reload} />
          </div>
        </div>
      </div>
    </div>
  );
}

function sevRank(s: string): number {
  return { BLOCKER: 0, MAJOR: 1, MINOR: 2, INFO: 3 }[s] ?? 4;
}

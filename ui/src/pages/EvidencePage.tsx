import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ClassificationBadge, RoleTag, SeverityBadge } from "../components/Badges";
import { DecisionPanel } from "../components/DecisionPanel";
import { EvidenceCard } from "../components/EvidenceCard";
import { ErrorBox, Loading } from "../components/Feedback";
import { HotkeyHelp, HotkeyHint } from "../components/HotkeyHelp";
import { useHotkeys } from "../lib/hotkeys";
import { ActionItemPanel, SaveRelationshipPanel } from "../components/RowActions";
import { enc, fmtScore } from "../lib/format";
import { PAGE_SIZE, queueParams, queueQueryFromParams } from "../lib/queue";
import { useReviewer } from "../lib/reviewer";
import { useAsync } from "../lib/useAsync";
import type { ViewerParams } from "../types";

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
  if (!detail.data) return <Loading label="Loading row…" />;
  const d = detail.data;
  const res = d.result;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <HotkeyHelp open={help} onClose={() => setHelp(false)} />
        <Link className="btn" to={queueLink} title="Back to the queue (Esc)">
          ← Queue
        </Link>
        <h1 className="mono">{res.row_id}</h1>
        <HotkeyHint />
        <span className="text-xs">
          SKU <b className="mono">{res.sku}</b>
        </span>
        <span className="mono text-xs">{res.check}</span>
        <RoleTag value={res.role} />
        {res.discrepancies.length > 0 && <SeverityBadge value={[...res.discrepancies].sort((a, b) => sevRank(a.severity) - sevRank(b.severity))[0].severity} />}
        <div className="ml-auto flex items-center gap-1 text-xs">
          {nb.data?.index !== null && nb.data && (
            <span className="text-gray-500 mr-1">
              {nb.data.index} / {nb.data.total} in queue
            </span>
          )}
          {nb.data && nb.data.index === null && !nb.loading && <span className="text-gray-400 mr-1">not in the current queue filter</span>}
          {nb.data?.prev ? (
            <Link className="btn" to={rowLink(nb.data.prev)} title="Previous row (k or [)">
              ← Prev
            </Link>
          ) : (
            <button className="btn" disabled>
              ← Prev
            </button>
          )}
          {nb.data?.next ? (
            <Link className="btn" to={rowLink(nb.data.next)} title="Next row ( ] )">
              Next →
            </Link>
          ) : (
            <button className="btn" disabled>
              Next →
            </button>
          )}
        </div>
      </div>

      {/* ---- what / why: the engine's recommendation */}
      <div className="panel">
        <div className="panel-title">
          Comparison — system recommendation (engine)
          <span className="ml-auto normal-case font-normal text-gray-600">
            match level <span className="mono">{res.match_level}</span> · score <span className="tabular-nums">{fmtScore(res.score)}</span>
            {res.relationship_id && (
              <>
                {" "}
                · via relationship{" "}
                <Link className="mono underline" to={`/terminology?id=${enc(res.relationship_id)}`}>
                  {res.relationship_id}
                </Link>
              </>
            )}
          </span>
        </div>
        <div className="p-3 grid gap-4 lg:grid-cols-[14rem_1fr]">
          <div>
            <div className="label">Engine classification</div>
            <div className="mt-1">
              <ClassificationBadge value={res.classification} size="lg" title="Engine recommendation — not a reviewer decision" />
            </div>
            <div className={`text-2xs mt-1 ${res.requires_validation ? "text-red-800 font-semibold" : "text-green-800"}`}>
              {res.requires_validation ? "Requires human validation" : "Auto-cleared: no validation required"}
            </div>
            {d.effective_classification !== res.classification && (
              <div className="mt-2">
                <div className="label">After reviewer override</div>
                <ClassificationBadge value={d.effective_classification} />
              </div>
            )}
            {(res.normalized_a || res.normalized_b) && (
              <div className="mt-2 text-2xs text-gray-600">
                <div className="label">Normalised text compared</div>
                <div>
                  A <span className="mono">{res.normalized_a ?? "—"}</span>
                </div>
                <div>
                  B <span className="mono">{res.normalized_b ?? "—"}</span>
                </div>
              </div>
            )}
          </div>
          <div className="min-w-0">
            <div className="label">Why</div>
            <p className="text-sm font-medium mt-0.5">{res.explanation}</p>
            {res.discrepancies.length > 0 ? (
              <table className="tbl mt-2">
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
                      <td>{x.detail}</td>
                      <td className="text-gray-800">{x.recommended_action || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-xs text-gray-500 mt-1">No discrepancy recorded by the engine.</div>
            )}
          </div>
        </div>
      </div>

      {/* ---- evidence */}
      <div className="grid xl:grid-cols-2 gap-3">
        <EvidenceCard side="A" runId={runId} rowId={rowId} ev={d.evidence.a} itemId={res.source_a?.id} />
        <EvidenceCard side="B" runId={runId} rowId={rowId} ev={d.evidence.b} itemId={res.source_b?.id} />
      </div>

      {/* ---- decide, and what happens after */}
      <div className="grid xl:grid-cols-[3fr_2fr] gap-3">
        <DecisionPanel runId={runId} rowId={rowId} detail={d} onChanged={detail.reload} />
        <div className="space-y-3">
          <SaveRelationshipPanel runId={runId} detail={d} onCreated={detail.reload} />
          <ActionItemPanel runId={runId} detail={d} onCreated={detail.reload} />
        </div>
      </div>
    </div>
  );
}

function sevRank(s: string): number {
  return { BLOCKER: 0, MAJOR: 1, MINOR: 2, INFO: 3 }[s] ?? 4;
}

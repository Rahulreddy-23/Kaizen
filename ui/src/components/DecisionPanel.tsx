import { useEffect, useState } from "react";
import { api } from "../api";
import { fmtDate } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { errorMessage } from "../lib/useAsync";
import { CLASSIFICATIONS, DECISION_KINDS, DECISION_LABELS, type Classification, type Decision, type DecisionKind, type HistoryEvent, type RowDetail, type Slot } from "../types";
import { ClassificationBadge, DecisionBadge, StateBadge } from "./Badges";
import { ErrorBox, Notice } from "./Feedback";

interface Props {
  runId: string;
  rowId: string;
  detail: RowDetail;
  onChanged: () => void;
}

/** Reviewer decisions are stored beside the engine recommendation, never over it. */
export function DecisionPanel({ runId, rowId, detail, onChanged }: Props) {
  const { reviewer, viewerParams, name } = useReviewer();
  const slotKey = String(reviewer.slot) as Slot;
  const mine = detail.decisions[slotKey];

  const [decision, setDecision] = useState<DecisionKind | null>(mine?.decision ?? null);
  const [override, setOverride] = useState<Classification>(mine?.override_classification ?? "EQUIVALENT");
  const [comment, setComment] = useState(mine?.comment ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const [finalDecision, setFinalDecision] = useState<DecisionKind>("ACCEPT");
  const [finalNote, setFinalNote] = useState("");
  const [finalBusy, setFinalBusy] = useState(false);
  const [finalErr, setFinalErr] = useState<string | null>(null);

  useEffect(() => {
    setDecision(mine?.decision ?? null);
    setOverride(mine?.override_classification ?? "EQUIVALENT");
    setComment(mine?.comment ?? "");
    setErr(null);
    setOk(null);
    setFinalErr(null);
    const d2 = detail.decisions["2"];
    const d1 = detail.decisions["1"];
    setFinalDecision(detail.final?.final_decision ?? d2?.decision ?? d1?.decision ?? "ACCEPT");
    setFinalNote(detail.final?.note ?? "");
  }, [rowId, reviewer.slot, mine?.decision, mine?.override_classification, mine?.comment, detail.decisions, detail.final]);

  const submit = async () => {
    if (!decision || !name) return;
    setBusy(true);
    setErr(null);
    setOk(null);
    try {
      const res = await api.postDecision(runId, {
        row_id: rowId,
        slot: reviewer.slot,
        reviewer: name,
        decision,
        comment,
        override_classification: decision === "OVERRIDE" ? override : undefined,
        blind: viewerParams.blind,
      });
      setOk(`Recorded as reviewer ${reviewer.slot}. Row state is now ${res.state.replace(/_/g, " ")}.`);
      onChanged();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const finalize = async () => {
    if (!name) return;
    setFinalBusy(true);
    setFinalErr(null);
    try {
      await api.finalize(runId, { row_id: rowId, final_decision: finalDecision, by: name, note: finalNote });
      onChanged();
    } catch (e) {
      setFinalErr(errorMessage(e));
    } finally {
      setFinalBusy(false);
    }
  };

  const blindHidden = viewerParams.blind && detail.decisions["2"] === null;
  const isFinal = detail.state === "FINALIZED";

  return (
    <div className="panel">
      <div className="panel-title">
        Reviewer decision
        <span className="ml-auto normal-case font-normal flex items-center gap-2">
          State <StateBadge value={detail.state} />
        </span>
      </div>
      {detail.state === "DISAGREEMENT" && (
        <div className="mx-3 mt-3 border-2 border-red-700 bg-red-50 text-red-900 px-3 py-2 text-xs">
          <div className="font-bold text-sm">DISAGREEMENT</div>
          Reviewer 1 and reviewer 2 decided differently. Discuss, then record the final decision below.
        </div>
      )}
      <div className="p-3 grid gap-4 lg:grid-cols-2">
        {/* ---- your decision */}
        <div className="space-y-2">
          <div className="text-xs">
            Deciding as{" "}
            {name ? <b>{name}</b> : <span className="text-red-800 font-semibold">(no name: enter your name in the top bar)</span>} · slot {reviewer.slot}{" "}
            {viewerParams.blind && <span className="chip border-blue-700 text-blue-800">BLIND</span>}
          </div>
          <div className="flex flex-wrap gap-1">
            {DECISION_KINDS.map((k) => (
              <button key={k} type="button" className={`btn ${decision === k ? "btn-primary" : ""}`} onClick={() => setDecision(k)} disabled={isFinal}>
                {DECISION_LABELS[k]}
              </button>
            ))}
          </div>
          {decision === "OVERRIDE" && (
            <label className="flex items-center gap-2 text-xs">
              Override classification to
              <select className="input" value={override} onChange={(e) => setOverride(e.target.value as Classification)}>
                {CLASSIFICATIONS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
          )}
          <textarea className="input w-full" rows={2} placeholder="Comment (why) — recorded verbatim in the audit trail" value={comment} onChange={(e) => setComment(e.target.value)} disabled={isFinal} />
          <div className="flex items-center gap-2">
            <button className="btn btn-primary" disabled={!decision || !name || busy || isFinal} onClick={submit}>
              {busy ? "Saving…" : mine ? "Update my decision" : "Submit decision"}
            </button>
            {mine && (
              <span className="text-2xs text-gray-500">
                You decided <b>{mine.decision}</b> at {fmtDate(mine.decided_at)}
              </span>
            )}
          </div>
          {err && <ErrorBox error={err} />}
          {ok && <Notice kind="good">{ok}</Notice>}
        </div>

        {/* ---- both reviewers + finalize */}
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <ReviewerBox label="Reviewer 1 (facilitator)" d={detail.decisions["1"]} hidden={blindHidden} />
            <ReviewerBox label="Reviewer 2 (independent)" d={detail.decisions["2"]} hidden={false} />
          </div>
          <div className="text-xs flex items-center gap-2">
            <span className="text-gray-500">Effective classification after overrides</span>
            <ClassificationBadge value={detail.effective_classification} />
            {detail.effective_classification !== detail.result.classification && <span className="text-2xs text-gray-500">(engine said {detail.result.classification})</span>}
          </div>
          <div className="border-t border-gray-200 pt-2">
            <div className="label mb-1">Final decision</div>
            {detail.final ? (
              <div className="text-xs">
                <DecisionBadge value={detail.final.final_decision} /> by <b>{detail.final.finalized_by}</b> at {fmtDate(detail.final.finalized_at)}
                {detail.final.note && <div className="text-gray-700 mt-0.5">“{detail.final.note}”</div>}
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-1">
                <select className="input" value={finalDecision} onChange={(e) => setFinalDecision(e.target.value as DecisionKind)}>
                  {DECISION_KINDS.map((k) => (
                    <option key={k} value={k}>
                      {DECISION_LABELS[k]}
                    </option>
                  ))}
                </select>
                <input className="input flex-1 min-w-[8rem]" placeholder="Note" value={finalNote} onChange={(e) => setFinalNote(e.target.value)} />
                <button className="btn" disabled={!name || finalBusy} onClick={finalize} title="Records the final decision for this row (closes the two-reviewer loop)">
                  {finalBusy ? "Finalizing…" : "Finalize"}
                </button>
              </div>
            )}
            {finalErr && <div className="mt-1"><ErrorBox error={finalErr} /></div>}
          </div>
          <Timeline history={detail.history} />
        </div>
      </div>
    </div>
  );
}

function ReviewerBox({ label, d, hidden }: { label: string; d: Decision | null; hidden: boolean }) {
  return (
    <div className="border border-gray-200 px-2 py-1.5 text-xs">
      <div className="label">{label}</div>
      {hidden ? (
        <div className="text-blue-800 mt-0.5">Hidden until you submit (blind mode)</div>
      ) : d ? (
        <div className="mt-0.5 space-y-0.5">
          <div>
            <DecisionBadge value={d.decision} />
            {d.override_classification && (
              <>
                {" "}
                → <ClassificationBadge value={d.override_classification} />
              </>
            )}
            {d.blind && <span className="chip ml-1">blind</span>}
          </div>
          <div className="text-gray-600">
            {d.reviewer} · {fmtDate(d.decided_at)}
          </div>
          {d.comment && <div className="text-gray-800">“{d.comment}”</div>}
        </div>
      ) : (
        <div className="text-gray-400 mt-0.5">No decision yet</div>
      )}
    </div>
  );
}

const STEPS = [
  { key: "engine", label: "Engine" },
  { key: "reviewer_1", label: "Reviewer 1" },
  { key: "reviewer_2", label: "Reviewer 2" },
  { key: "final", label: "Final" },
];

function Timeline({ history }: { history: HistoryEvent[] }) {
  const byEvent = new Map(history.map((h) => [h.event, h]));
  return (
    <div>
      <div className="label mb-1">History</div>
      <ol className="text-xs space-y-1">
        {STEPS.map((s) => {
          const h = byEvent.get(s.key);
          return (
            <li key={s.key} className="flex gap-2">
              <span className={`mt-1 inline-block w-2 h-2 rounded-full shrink-0 ${h ? "bg-gray-900" : "bg-gray-300"}`} />
              <span className={h ? "" : "text-gray-400"}>
                <b>{s.label}</b>{" "}
                {!h && "— pending"}
                {h && s.key === "engine" && `— ${h.detail ?? "recommendation recorded with the run"}`}
                {h && (s.key === "reviewer_1" || s.key === "reviewer_2") && (
                  <>
                    — {h.decision}
                    {h.override_classification ? ` → ${h.override_classification}` : ""} by {h.reviewer} at {fmtDate(h.decided_at)}
                    {h.blind ? " (blind)" : ""}
                    {h.comment ? ` · “${h.comment}”` : ""}
                  </>
                )}
                {h && s.key === "final" && (
                  <>
                    — {h.final_decision} by {h.finalized_by} at {fmtDate(h.finalized_at)}
                    {h.note ? ` · “${h.note}”` : ""}
                  </>
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

import { CheckSquare, SealCheck } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { enc } from "../lib/format";
import { useToast } from "../lib/toast";
import { errorMessage } from "../lib/useAsync";
import { ActionMenu } from "./ActionMenu";
import { ErrorBox, Loading } from "./Feedback";
import { Button, Dialog } from "./ui";

export function BulkReviewActions({runId, canEdit, onChanged, approveOnly = false}: {
  runId: string; canEdit: boolean; onChanged: () => void; approveOnly?: boolean;
}) {
  const [action, setAction] = useState<"accept" | "approve" | null>(null);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof api.bulkReviewPreview>> | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const toast = useToast();
  useEffect(() => {
    let current = true;
    setPreview(null); setConfirmed(false); setError(null);
    if (action) api.bulkReviewPreview(runId).then(value => { if (current) setPreview(value); }).catch(e => { if (current) setError(errorMessage(e)); });
    return () => { current = false; };
  }, [action, runId, attempt]);
  if (!canEdit) return null;
  const count = preview ? action === "approve" ? preview.approve_count : preview.accept_count : 0;
  const submit = async () => {
    if (!preview || !count || busy || (action === "approve" && !confirmed)) return;
    setBusy(true); setError(null);
    try {
      if (action === "approve") {
        const result = await api.bulkApprove(runId, preview.revision);
        toast({tone: "ok", title: `${result.approved} row${result.approved === 1 ? "" : "s"} approved`, description: <a href={`#/runs/${enc(runId)}/review?nv=0&state=FINALIZED`}>View approved rows</a>});
      } else {
        const result = await api.bulkAccept(runId);
        toast({tone: "ok", title: `${result.accepted} Accept decisions saved`, description: "These rows are Reviewed and awaiting approval. Use Approve auto-cleared rows to approve eligible pairs."});
      }
      setAction(null);
      onChanged();
    } catch (e) { setError(errorMessage(e)); setPreview(null); setConfirmed(false); }
    finally { setBusy(false); }
  };
  return <>
    {approveOnly ? <Button size="sm" className="mt-3" onClick={() => setAction("approve")} icon={<SealCheck size={16}/>}>Approve auto-cleared rows</Button> : <ActionMenu label="Bulk review" items={[
      {label: "Accept auto-cleared rows", icon: <CheckSquare size={17}/>, onSelect: () => setAction("accept")},
      {label: "Approve auto-cleared rows", icon: <SealCheck size={17}/>, onSelect: () => setAction("approve")},
    ]}/>}
    <Dialog open={action !== null} closeDisabled={busy} onClose={() => setAction(null)} width="sm" title={action === "approve" ? "Approve auto-cleared rows" : "Accept auto-cleared rows"} footer={<>
      <Button disabled={busy} onClick={() => setAction(null)}>Cancel</Button>
      <Button variant="primary" loading={busy} disabled={busy || !preview || !count || (action === "approve" && !confirmed)} onClick={() => void submit()}>{action === "approve" ? `Approve ${count} row${count === 1 ? "" : "s"}` : `Save ${count} Accept decision${count === 1 ? "" : "s"}`}</Button>
    </>}>
      <div className="space-y-4">
        <p>Applies to eligible paired Exact or Equivalent component comparisons across this run.</p>
        <p className="text-ink-2">Flagged, unpaired, exempt and already approved rows are skipped. Existing decisions other than Accept are kept.</p>
        {action === "approve" ? <><p>Records an Accept decision where needed and approves each eligible row. Approved counts and the Approved list update together.</p><label className="flex gap-3 text-sm"><input type="checkbox" className="mt-1" checked={confirmed} disabled={busy || !preview} onChange={e => setConfirmed(e.target.checked)}/><span>I reviewed these pairings and confirm bulk approval. Approval of my own work will be recorded as self-approved.</span></label></> : <p>Records Accept decisions for unreviewed rows. These remain <strong>Reviewed · awaiting approval</strong> until someone explicitly approves them.</p>}
        {preview && <p role="status"><strong>{count}</strong> eligible row{count === 1 ? "" : "s"}{count ? "." : " — nothing to change."}</p>}
        {!preview && !error && action && <Loading label="Loading eligible rows" lines={2}/>}
        {error && <ErrorBox error={error} onRetry={() => setAttempt(v => v + 1)}/>}
      </div>
    </Dialog>
  </>;
}

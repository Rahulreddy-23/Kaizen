import { Trash } from "@phosphor-icons/react";
import { useState } from "react";
import { api } from "../api";
import { useToast } from "../lib/toast";
import { errorMessage } from "../lib/useAsync";
import type { RunListItem } from "../types";
import { ErrorBox } from "./Feedback";
import { Button, Dialog, Field } from "./ui";

export function PermanentDeleteRun({ run, onDeleted }: {
  run: Pick<RunListItem, "run_id" | "name" | "permission">;
  onDeleted: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  if (run.permission !== "owner") return null;
  const label = run.name || run.run_id;
  const remove = async () => {
    if (busy || confirmation !== "DELETE") return;
    setBusy(true); setError(null);
    try {
      const result = await api.permanentlyDeleteRun(run.run_id);
      toast({ tone: result.cleanup_pending || result.files_retained ? "warn" : "ok", title: "Run permanently deleted", description: result.cleanup_pending ? "File cleanup is pending after a storage error. It will retry when the service restarts." : result.files_retained ? "Review data was removed. Some files were kept because another run uses them or their references could not be verified." : "Its stored files and review data have been removed. Independent copies and original local folders are kept." });
      setOpen(false);
      onDeleted();
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  };
  return <>
    <Button variant="danger" icon={<Trash size={17}/>} aria-label={`Permanently delete ${label}`} onClick={() => { setConfirmation(""); setError(null); setOpen(true); }}>Delete permanently</Button>
    <Dialog open={open} closeDisabled={busy} onClose={() => setOpen(false)} title="Permanently delete this run?" width="sm" footer={<>
      <Button disabled={busy} onClick={() => setOpen(false)}>Keep run</Button>
      <Button variant="danger" loading={busy} disabled={busy || confirmation !== "DELETE"} onClick={() => void remove()}>Delete permanently</Button>
    </>}>
      <div className="space-y-4">
        <p><strong className="break-words">{label}</strong> will be removed for everyone. This cannot be undone.</p>
        <p className="text-ink-2">Deletes this run’s stored uploads, extracted results, exports, review history and closed-testing records to free storage.</p>
        <p className="text-ink-2">Independent copies, files still used by another run, approved shared terminology and original local folders are kept.</p>
        <Field label="Type DELETE to confirm"><input className="input w-full" autoComplete="off" spellCheck={false} value={confirmation} disabled={busy} onChange={e => setConfirmation(e.target.value)}/></Field>
        {error && <ErrorBox error={error}/>}
      </div>
    </Dialog>
  </>;
}

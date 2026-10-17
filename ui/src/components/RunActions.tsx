import { PencilSimple, Trash } from "@phosphor-icons/react";
import { useState } from "react";
import { api } from "../api";
import { useToast } from "../lib/toast";
import { errorMessage } from "../lib/useAsync";
import type { RunListItem } from "../types";
import { ErrorBox } from "./Feedback";
import { Button, Dialog, Field } from "./ui";
import { ActionMenu } from "./ActionMenu";

export function RunActions({ run, compact = false, onChanged, onDeleted }: {
  run: Pick<RunListItem, "run_id" | "name" | "permission">;
  compact?: boolean;
  onChanged?: () => void;
  onDeleted?: () => void;
}) {
  const [action, setAction] = useState<"rename" | "delete" | null>(null);
  const [name, setName] = useState(run.name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  if (run.permission !== "owner") return null;
  const label = run.name || run.run_id;
  const open = (value: "rename" | "delete") => { setName(run.name); setError(null); setAction(value); };
  const close = () => { if (!busy) setAction(null); };
  const save = async () => {
    setBusy(true); setError(null);
    try {
      if (action === "rename") {
        await api.renameRun(run.run_id, name.trim());
        toast({ tone: "ok", title: "Run renamed" });
        onChanged?.();
      } else if (action === "delete") {
        await api.deleteRun(run.run_id);
        toast({ tone: "ok", title: "Run moved to Deleted runs", description: "You can restore it from All runs → Deleted runs." });
        onDeleted?.();
      }
      setAction(null);
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  };
  return <div className="run-actions">
    <ActionMenu compact={compact} label={compact ? `Options for ${label}` : "Options"} items={[
      {label: "Rename run", icon: <PencilSimple size={17}/>, onSelect: () => open("rename")},
      {label: "Delete run", icon: <Trash size={17}/>, danger: true, onSelect: () => open("delete")},
    ]}/>
    <Dialog open={action !== null} onClose={close} title={action === "rename" ? "Rename run" : "Delete run?"} width="sm" footer={<>
      <Button disabled={busy} onClick={close}>Cancel</Button>
      <Button variant={action === "delete" ? "danger" : "primary"} loading={busy} disabled={busy || (action === "rename" && (!name.trim() || name.trim() === run.name))} onClick={() => void save()}>{action === "rename" ? "Save name" : "Delete run"}</Button>
    </>}>
      {action === "rename" ? <Field label="Run name"><input className="input w-full" value={name} maxLength={120} disabled={busy} onChange={event => setName(event.target.value)} /></Field> : <div className="space-y-3">
        <p>Move <strong className="break-words">{label}</strong> to Deleted runs?</p>
        <p className="text-ink-2">It will no longer be accessible to you or anyone you shared it with. Documents and review history are retained so you can restore it from All runs → Deleted runs.</p>
      </div>}
      {error && <ErrorBox error={error} />}
    </Dialog>
  </div>;
}

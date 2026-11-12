import { ArrowsCounterClockwise } from "@phosphor-icons/react";
import { useState } from "react";
import { api, type RunProgress } from "../api";
import { useToast } from "../lib/toast";
import { errorMessage } from "../lib/useAsync";
import type { RunListItem } from "../types";
import { RunProgressIndicator } from "./RunProgressIndicator";
import { Button } from "./ui";

/** Processes the run's stored source documents again. Each rerun is numbered under the original run
 * and can be chosen in Download Excel on its Overview. */
export function RerunButton({ run, compact = false, onDone }: {
  run: Pick<RunListItem, "run_id" | "name" | "permission">;
  compact?: boolean;
  onDone?: () => void;
}) {
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  if (run.permission === "view") return null;
  const start = async () => {
    setBusy(true);
    setProgress({ percent: 0, stage: "Preparing documents" });
    try {
      const result = await api.rerunRun(run.run_id, setProgress);
      toast({ tone: "ok", title: result.rerun_number ? `Rerun ${result.rerun_number} complete` : "Rerun complete", description: "Choose it under Download Excel on the run's Overview." });
      onDone?.();
    } catch (e) {
      toast({ tone: "bad", title: "Rerun failed", description: errorMessage(e) });
    } finally {
      setBusy(false);
      setProgress(null);
    }
  };
  const label = run.name || run.run_id;
  return <span className="run-start-action">
    <Button icon={<ArrowsCounterClockwise size={16} />} iconOnly={compact} loading={busy} disabled={busy} onClick={() => void start()}
      aria-label={compact ? `Rerun ${label}` : undefined} title="Process this run's documents again">
      {compact ? null : "Rerun"}
    </Button>
    {busy && progress && <RunProgressIndicator value={progress} />}
  </span>;
}

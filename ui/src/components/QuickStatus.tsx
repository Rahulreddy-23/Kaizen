import {CheckCircle, Circle, WarningCircle} from "@phosphor-icons/react";
import type {QuickKind, QuickStatus} from "../types";

export const QUICK_KINDS: QuickKind[] = ["BOM", "LABEL", "DRAWING"];
export const QUICK_NAME = {BOM: "BOM", LABEL: "Label", DRAWING: "Diagram"};
export const QUICK_STATUS = {matched: "Matched", attention: "Missing or needs review", neutral: "Not compared"};

export function QuickStatusLabel({status}: {status: QuickStatus}) {
  const Icon = status === "matched" ? CheckCircle : status === "attention" ? WarningCircle : Circle;
  return <span className={`quick-status quick-${status}`}><Icon size={14} aria-hidden />{QUICK_STATUS[status]}</span>;
}

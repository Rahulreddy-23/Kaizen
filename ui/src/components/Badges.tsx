import type { Classification, DecisionKind, ReviewState, Severity } from "../types";

// Colour is used for meaning only. Classification and severity palettes are fixed here and in Stat.tsx.
const CLS: Record<Classification, string> = {
  EXACT: "bg-green-50 text-green-800 border-green-700",
  EQUIVALENT: "bg-teal-50 text-teal-800 border-teal-700",
  POTENTIAL: "bg-amber-50 text-amber-800 border-amber-600",
  MISMATCH: "bg-red-50 text-red-800 border-red-700",
  MISSING: "bg-orange-50 text-orange-800 border-orange-600",
};

export function ClassificationBadge({ value, title, size = "sm" }: { value: string | null | undefined; title?: string; size?: "sm" | "lg" }) {
  if (!value) return <span className="text-gray-400">—</span>;
  const cls = CLS[value as Classification] ?? "bg-gray-50 text-gray-700 border-gray-400";
  const sz = size === "lg" ? "px-2 py-0.5 text-sm" : "px-1.5 py-0 text-2xs";
  return (
    <span title={title} className={`inline-block border font-semibold tracking-wide rounded-sm whitespace-nowrap ${sz} ${cls}`}>
      {value}
    </span>
  );
}

const SEV: Record<Severity, string> = {
  BLOCKER: "bg-red-900 text-white border-red-900",
  MAJOR: "bg-red-700 text-white border-red-700",
  MINOR: "bg-amber-600 text-white border-amber-600",
  INFO: "bg-blue-700 text-white border-blue-700",
};

export function SeverityBadge({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="text-gray-400">—</span>;
  const cls = SEV[value as Severity] ?? "bg-gray-500 text-white border-gray-500";
  return <span className={`inline-block border px-1.5 py-0 text-2xs font-bold tracking-wide rounded-sm whitespace-nowrap ${cls}`}>{value}</span>;
}

const STATE: Record<ReviewState, string> = {
  ENGINE_RECOMMENDED: "text-gray-600 border-gray-400 bg-white",
  REVIEWER_1_COMPLETE: "text-gray-800 border-gray-500 bg-gray-100",
  REVIEWER_2_COMPLETE: "text-gray-800 border-gray-500 bg-gray-100",
  AGREED: "text-green-800 border-green-700 bg-green-50",
  DISAGREEMENT: "text-red-900 border-red-700 bg-red-50 font-bold",
  FINALIZED: "text-white border-gray-900 bg-gray-900",
};

export function StateBadge({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="text-gray-400">—</span>;
  const cls = STATE[value as ReviewState] ?? "text-gray-700 border-gray-400 bg-white";
  return <span className={`inline-block border px-1.5 py-0 text-2xs font-semibold tracking-wide rounded-sm whitespace-nowrap ${cls}`}>{value.replace(/_/g, " ")}</span>;
}

const DEC: Record<DecisionKind, string> = {
  ACCEPT: "text-green-800 border-green-700 bg-green-50",
  OVERRIDE: "text-amber-800 border-amber-600 bg-amber-50",
  CONFIRM_DISCREPANCY: "text-red-800 border-red-700 bg-red-50",
  NEEDS_MORE_INFORMATION: "text-blue-800 border-blue-700 bg-blue-50",
};

export function DecisionBadge({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="text-gray-400">—</span>;
  const cls = DEC[value as DecisionKind] ?? "text-gray-700 border-gray-400";
  return <span className={`inline-block border px-1.5 py-0 text-2xs font-semibold tracking-wide rounded-sm whitespace-nowrap ${cls}`}>{value.replace(/_/g, " ")}</span>;
}

export function DocTypeBadge({ value }: { value: string | null | undefined }) {
  if (!value) return null;
  return <span className="inline-block border border-gray-500 bg-gray-700 text-white px-1.5 py-0 text-2xs font-semibold tracking-wide rounded-sm whitespace-nowrap">{value}</span>;
}

export function RoleTag({ value }: { value: string }) {
  if (value === "item") return null;
  return <span className="chip" title="Row role">{value}</span>;
}

export function StatusBadge({ value }: { value: string }) {
  const map: Record<string, string> = {
    OPEN: "text-red-800 border-red-700 bg-red-50",
    IN_PROGRESS: "text-amber-800 border-amber-600 bg-amber-50",
    RESOLVED: "text-green-800 border-green-700 bg-green-50",
    CLOSED: "text-white border-gray-900 bg-gray-900",
    REJECTED: "text-gray-600 border-gray-400 bg-gray-100",
  };
  return <span className={`inline-block border px-1.5 py-0 text-2xs font-semibold tracking-wide rounded-sm whitespace-nowrap ${map[value] ?? "border-gray-400"}`}>{value.replace(/_/g, " ")}</span>;
}

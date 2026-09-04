import type { ReactNode } from "react";

export const CLASS_COLORS: Record<string, string> = {
  EXACT: "#15803d",
  EQUIVALENT: "#0f766e",
  POTENTIAL: "#b45309",
  MISMATCH: "#b91c1c",
  MISSING: "#c2410c",
};
export const SEV_COLORS: Record<string, string> = { BLOCKER: "#7f1d1d", MAJOR: "#b91c1c", MINOR: "#b45309", INFO: "#1d4ed8" };

export function Stat({
  label,
  value,
  sub,
  tone = "neutral",
  className = "",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad";
  className?: string;
}) {
  const tones = { neutral: "text-gray-900", good: "text-green-800", warn: "text-amber-700", bad: "text-red-800" };
  return (
    <div className={`panel px-3 py-2 ${className}`}>
      <div className="label">{label}</div>
      <div className={`text-xl font-semibold tabular-nums leading-tight ${tones[tone]}`}>{value}</div>
      {sub && <div className="text-2xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}

export interface BarSegment {
  label: string;
  value: number;
  color: string;
}

/** Proportional bar. No charting library: widths are percentages of the total. */
export function Bar({ segments, height = 10, legend = true }: { segments: BarSegment[]; height?: number; legend?: boolean }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  return (
    <div>
      <div className="flex w-full overflow-hidden bg-gray-200 rounded-sm" style={{ height }}>
        {segments
          .filter((s) => s.value > 0)
          .map((s) => (
            <div key={s.label} title={`${s.label}: ${s.value}`} style={{ width: `${(100 * s.value) / total}%`, background: s.color }} />
          ))}
      </div>
      {legend && (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-2xs text-gray-600">
          {segments.map((s) => (
            <span key={s.label} className="inline-flex items-center gap-1">
              <span className="inline-block w-2 h-2" style={{ background: s.color }} />
              {s.label} <span className="tabular-nums font-semibold text-gray-800">{s.value}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Single horizontal bar used in dense tables (value / max). */
export function MiniBar({ value, max, color = "#374151", width = 80 }: { value: number; max: number; color?: string; width?: number }) {
  const w = max > 0 ? Math.min(100, (100 * value) / max) : 0;
  return (
    <span className="inline-block align-middle bg-gray-200 h-2 rounded-sm" style={{ width }}>
      <span className="block h-2 rounded-sm" style={{ width: `${w}%`, background: color }} />
    </span>
  );
}

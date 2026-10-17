import type { RunProgress } from "../api";

export function RunProgressIndicator({value}: {value: RunProgress}) {
  return <span className="run-progress" role="status" aria-live="polite" title={value.stage}>
    <progress max={100} value={value.percent} aria-label="Cross-check progress" aria-valuetext={`${value.percent}% · ${value.stage}`} />
    <span className="tabular-nums">{value.percent}%</span><span className="sr-only"> · {value.stage}</span>
  </span>;
}

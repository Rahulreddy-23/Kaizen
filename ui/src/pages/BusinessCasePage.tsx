import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, Loading } from "../components/Feedback";
import { MiniBar, Stat } from "../components/Stat";
import { fmtMoney } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { BusinessParams } from "../types";

const FIELDS: { key: keyof BusinessParams; label: string; def: number; step?: number }[] = [
  { key: "baseline_minutes_per_sku", label: "Baseline minutes per SKU per reviewer", def: 60 },
  { key: "reviewers", label: "Reviewers per SKU", def: 2 },
  { key: "hourly_rate", label: "Hourly rate ($)", def: 37.5, step: 0.5 },
  { key: "skus_per_project", label: "SKUs per project", def: 100 },
  { key: "projects_per_year", label: "Projects per year", def: 20 },
  { key: "minutes_per_validation_row", label: "Minutes per row needing validation", def: 1.5, step: 0.1 },
  { key: "minutes_per_cleared_row", label: "Minutes per auto-cleared row (skim)", def: 0.1, step: 0.05 },
  { key: "target_reduction_pct", label: "Target reduction (%)", def: 50 },
];

function paramsFrom(sp: URLSearchParams): BusinessParams {
  const out: BusinessParams = {};
  for (const f of FIELDS) {
    const v = sp.get(f.key);
    if (v !== null && v !== "" && !Number.isNaN(Number(v))) out[f.key] = Number(v);
  }
  return out;
}

export default function BusinessCasePage() {
  const { runId = "" } = useParams();
  const [sp, setSp] = useSearchParams();
  const params = paramsFrom(sp);
  const bc = useAsync(() => api.businessCase(runId, params), [runId, sp.toString()]);
  const [form, setForm] = useState<Record<string, string>>({});
  useEffect(() => {
    const f: Record<string, string> = {};
    for (const x of FIELDS) f[x.key] = String(params[x.key] ?? x.def);
    setForm(f);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp.toString()]);

  const recompute = () => {
    const n = new URLSearchParams();
    for (const x of FIELDS) {
      const v = Number(form[x.key]);
      if (!Number.isNaN(v) && v !== x.def) n.set(x.key, String(v));
    }
    setSp(n);
  };

  const d = bc.data;
  const target = params.target_reduction_pct ?? 50;
  return (
    <div className="space-y-3">
      <div className="flex items-baseline gap-3 flex-wrap">
        <h1>Business case</h1>
        <span className="text-xs text-gray-500">Computed from this run's actual rows. Nothing here assumes accuracy; it only counts what the engine cleared and what still needs a person.</span>
      </div>
      {bc.error && <ErrorBox error={bc.error} onRetry={bc.reload} />}
      {!d && !bc.error && <Loading />}
      {d && (
        <>
          <div className={`panel border-2 ${d.meets_target ? "border-green-700" : "border-red-700"}`}>
            <div className="p-4 grid md:grid-cols-[1fr_auto] gap-4 items-center">
              <div>
                <div className="label">Meets the {target}% reduction target?</div>
                <div className={`text-3xl font-bold ${d.meets_target ? "text-green-800" : "text-red-800"}`}>{d.meets_target ? "YES" : "NO"}</div>
                <div className={`text-sm ${d.meets_target ? "text-green-900" : "text-red-900"}`}>
                  Estimated reduction <b className="tabular-nums">{d.reduction_pct}%</b> against a target of {target}%
                  {!d.meets_target && ` — short by ${(target - d.reduction_pct).toFixed(1)} points with the current assumptions.`}
                </div>
              </div>
              <div className="text-xs text-gray-600 max-w-sm">
                {d.needs_validation} of {d.rows} comparisons still need a person ({Math.round((100 * d.needs_validation) / Math.max(1, d.rows))}%). The lever is the validation rate: every relationship
                approved and every parser warning fixed moves rows from “needs validation” to “auto-cleared”.
              </div>
            </div>
          </div>

          {d.confirmable_rows !== undefined && (
            <div className="panel">
              <div className="panel-title">
                Projection — after reviewers confirm strong pairings as relationships
                <span className="ml-auto normal-case font-normal text-gray-500">a projection, not a measurement: it assumes {d.confirmable_rows} strong fuzzy pairings are confirmed once and saved as relationships</span>
              </div>
              <div className="p-3 grid grid-cols-2 md:grid-cols-6 gap-2 text-xs">
                <Stat label="Confirmable rows" value={d.confirmable_rows} sub="fuzzy, no discrepancy, score ≥ 0.95" />
                <Stat label="Needs validation after" value={d.needs_validation_after_confirmation ?? "—"} tone="warn" />
                <Stat label="Est. minutes / SKU after" value={d.estimated_minutes_per_sku_after_confirmation ?? "—"} />
                <Stat label="Reduction after" value={`${d.reduction_pct_after_confirmation ?? "—"}%`} tone={d.meets_target_after_confirmation ? "good" : "bad"} sub={d.meets_target_after_confirmation ? `meets ${target}% target` : `still below ${target}% target`} />
                <Stat label="Hours saved / project after" value={d.hours_saved_per_project_after_confirmation ?? "—"} />
                <Stat label="Annual savings after" value={d.annual_savings_after_confirmation !== undefined ? fmtMoney(d.annual_savings_after_confirmation) : "—"} />
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-2">
            <Stat label="SKUs" value={d.skus} />
            <Stat label="Reviewable comparisons" value={d.rows} sub="item + change rows" />
            <Stat label="Auto-cleared" value={d.auto_cleared} tone="good" />
            <Stat label="Needs validation" value={d.needs_validation} tone="bad" />
            <Stat label="Est. minutes / SKU" value={d.estimated_minutes_per_sku} sub={`baseline ${d.baseline_minutes_per_sku}`} />
            <Stat label="Minutes saved / SKU" value={d.minutes_saved_per_sku} tone={d.minutes_saved_per_sku >= 0 ? "good" : "bad"} />
            <Stat label="Hours saved / project" value={d.hours_saved_per_project} sub={`${d.skus_per_project} SKUs × ${d.reviewers} reviewers`} />
            <Stat label="Annual savings" value={fmtMoney(d.annual_savings)} sub={`${d.projects_per_year} projects × $${d.hourly_rate}/h`} tone={d.annual_savings >= 0 ? "good" : "bad"} />
          </div>

          <div className="grid xl:grid-cols-[24rem_1fr] gap-3 items-start">
            <div className="panel">
              <div className="panel-title">Assumptions (editable)</div>
              <div className="p-3 space-y-2 text-xs">
                {FIELDS.map((f) => (
                  <label key={f.key} className="grid grid-cols-[1fr_6rem] items-center gap-2">
                    <span className="text-gray-700">{f.label}</span>
                    <input type="number" step={f.step ?? 1} className="input tabular-nums text-right" value={form[f.key] ?? ""} onChange={(e) => setForm({ ...form, [f.key]: e.target.value })} />
                  </label>
                ))}
                <div className="flex gap-2 pt-1">
                  <button className="btn btn-primary" onClick={recompute}>
                    Recompute
                  </button>
                  <button className="btn" onClick={() => setSp(new URLSearchParams())}>
                    Reset to brief defaults
                  </button>
                </div>
                <div className="border-t border-gray-200 pt-2">
                  <div className="label mb-1">As applied by the calculator</div>
                  <ul className="list-disc pl-4 space-y-0.5 text-gray-700">
                    {d.assumptions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
            <div className="panel">
              <div className="panel-title">Per SKU — estimated review minutes vs. baseline {d.baseline_minutes_per_sku}</div>
              <table className="tbl">
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th className="text-right">Rows</th>
                    <th className="text-right">Auto-cleared</th>
                    <th className="text-right">Needs validation</th>
                    <th className="text-right">Est. minutes</th>
                    <th>vs. baseline</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(d.per_sku).map(([sku, p]) => {
                    const over = p.estimated_minutes > d.baseline_minutes_per_sku;
                    return (
                      <tr key={sku}>
                        <td className="mono">{sku}</td>
                        <td className="text-right tabular-nums">{p.rows}</td>
                        <td className="text-right tabular-nums text-green-800">{p.auto_cleared}</td>
                        <td className="text-right tabular-nums text-red-800">{p.needs_validation}</td>
                        <td className={`text-right tabular-nums ${over ? "text-red-800 font-semibold" : ""}`}>{p.estimated_minutes}</td>
                        <td>
                          <MiniBar value={p.estimated_minutes} max={d.baseline_minutes_per_sku} color={over ? "#b91c1c" : "#374151"} width={140} />
                          <span className="text-2xs text-gray-500 ml-1 tabular-nums">{Math.round((100 * p.estimated_minutes) / Math.max(1, d.baseline_minutes_per_sku))}%</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

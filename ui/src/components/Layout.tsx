import { useEffect, useState } from "react";
import { NavLink, Outlet, matchPath, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import { enc } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { useAsync } from "../lib/useAsync";

const LAST_RUN_KEY = "kaizen.lastRun";

export function Layout() {
  const loc = useLocation();
  const nav = useNavigate();
  const match = matchPath("/runs/:runId/*", loc.pathname) ?? matchPath("/runs/:runId", loc.pathname);
  const routeRun = match?.params.runId ?? null;
  const [lastRun, setLastRun] = useState<string | null>(() => {
    try {
      return localStorage.getItem(LAST_RUN_KEY);
    } catch {
      return null;
    }
  });
  useEffect(() => {
    if (!routeRun) return;
    setLastRun(routeRun);
    try {
      localStorage.setItem(LAST_RUN_KEY, routeRun);
    } catch {
      /* ignore */
    }
  }, [routeRun]);
  const runId = routeRun ?? lastRun;
  const runs = useAsync(() => api.listRuns(), [routeRun]);
  const { reviewer, setReviewer } = useReviewer();

  const r = (suffix: string) => (runId ? `/runs/${enc(runId)}${suffix}` : null);
  const item = (to: string | null, label: string, end = false) =>
    to ? (
      <NavLink
        to={to}
        end={end}
        className={({ isActive }) =>
          `block px-3 py-1.5 text-xs border-l-2 ${isActive ? "border-gray-900 bg-white font-semibold text-gray-900" : "border-transparent text-gray-700 hover:bg-gray-200"}`
        }
      >
        {label}
      </NavLink>
    ) : (
      <span className="block px-3 py-1.5 text-xs text-gray-400 border-l-2 border-transparent">{label}</span>
    );

  const ctl = "bg-gray-800 border border-gray-600 text-gray-100 px-1 py-0.5 rounded-sm text-xs";
  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-10 bg-gray-900 text-gray-100 flex items-center px-3 gap-4 text-xs shrink-0">
        <NavLink to="/" className="font-semibold tracking-wider text-white">
          KAIZEN CROSS-CHECK
        </NavLink>
        <span className="text-gray-400 hidden xl:inline">BOM · label · drawing · PCO cross-check. Engine output is a recommendation; reviewers decide.</span>
        <div className="ml-auto flex items-center gap-3">
          <label className="flex items-center gap-1">
            <span className="text-gray-400">Run</span>
            <select className={`${ctl} mono max-w-[16rem]`} value={runId ?? ""} onChange={(e) => e.target.value && nav(`/runs/${enc(e.target.value)}`)}>
              <option value="">— select —</option>
              {(runs.data ?? []).map((x) => (
                <option key={x.run_id} value={x.run_id}>
                  {x.run_id} · {x.summary.skus} SKUs · {x.summary.rows} rows
                </option>
              ))}
              {runId && !(runs.data ?? []).some((x) => x.run_id === runId) && <option value={runId}>{runId}</option>}
            </select>
          </label>
          <label className="flex items-center gap-1">
            <span className="text-gray-400">Reviewer</span>
            <input className={`${ctl} w-32`} placeholder="your name" value={reviewer.name} onChange={(e) => setReviewer({ ...reviewer, name: e.target.value })} />
          </label>
          <label className="flex items-center gap-1">
            <span className="text-gray-400">Slot</span>
            <select className={ctl} value={reviewer.slot} onChange={(e) => setReviewer({ ...reviewer, slot: e.target.value === "2" ? 2 : 1 })}>
              <option value="1">1 · facilitator</option>
              <option value="2">2 · independent</option>
            </select>
          </label>
          <label
            className={`flex items-center gap-1 ${reviewer.slot === 2 ? "" : "opacity-50"}`}
            title="Blind mode (slot 2 only): reviewer 1's decisions stay hidden until you have submitted yours"
          >
            <input type="checkbox" disabled={reviewer.slot !== 2} checked={reviewer.slot === 2 && reviewer.blind} onChange={(e) => setReviewer({ ...reviewer, blind: e.target.checked })} />
            Blind
          </label>
        </div>
      </header>
      <div className="flex flex-1 min-h-0">
        <nav className="w-44 shrink-0 bg-gray-100 border-r border-gray-300 py-2">
          <div className="label px-3 py-1">Workspace</div>
          {item("/", "Runs", true)}
          {item("/terminology", "Terminology")}
          {item("/action-items", "Action items")}
          <div className="label px-3 pt-3 pb-1">Run</div>
          <div className="px-3 pb-1 mono text-2xs text-gray-600 break-all">{runId ?? "none selected"}</div>
          {item(r(""), "Dashboard", true)}
          {item(r("/review"), "Review queue")}
          {item(r("/documents"), "Documents")}
          {item(r("/mining"), "Mining suggestions")}
          {item(r("/business"), "Business case")}
        </nav>
        <main className="flex-1 min-w-0 p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

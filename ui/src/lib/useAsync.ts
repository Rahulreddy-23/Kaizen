import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  refreshing: boolean;
  reload: () => void;
  refresh: () => void;
  setData: (d: T) => void;
}

export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

/** Keep data on refresh, but never expose a previous run or row after the loader's keys change. */
export function useAsync<T>(fn: () => Promise<T>, deps: DependencyList): AsyncState<T> {
  const [result, setResult] = useState<{ data: T | null; error: string | null; loading: boolean; refreshing: boolean; deps: DependencyList }>({ data: null, error: null, loading: true, refreshing: false, deps: [...deps] });
  const [request, setRequest] = useState({tick: 0, background: false});
  const seq = useRef(0);
  const currentDeps = useRef(deps);
  currentDeps.current = deps;
  const sameDeps = (a: DependencyList, b: DependencyList) => a.length === b.length && a.every((value, i) => Object.is(value, b[i]));
  const current = sameDeps(result.deps, deps);
  const data = current ? result.data : null;
  const error = current ? result.error : null;
  const loading = !current || result.loading;
  const setData = useCallback((value: T) => setResult({ data: value, deps: [...currentDeps.current], error: null, loading: false, refreshing: false }), []);
  useEffect(() => {
    const id = ++seq.current;
    let live = true;
    setResult(previous => {
      const data = sameDeps(previous.deps, deps) ? previous.data : null;
      return { data, error: null, loading: !request.background || data === null, refreshing: request.background && data !== null, deps: [...deps] };
    });
    Promise.resolve().then(fn).then(
      (d) => {
        if (!live || seq.current !== id) return;
        setResult({ data: d, error: null, loading: false, refreshing: false, deps: [...deps] });
      },
      (e) => {
        if (!live || seq.current !== id) return;
        // A revoked run or expired session must disappear even during a quiet refresh.
        const denied = typeof e === "object" && e !== null && "status" in e && [401,403,404].includes(Number(e.status));
        setResult(previous => ({ ...previous, data: denied ? null : previous.data, error: errorMessage(e), loading: false, refreshing: false, deps: [...deps] }));
      },
    );
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, request.tick]);
  const reload = useCallback(() => setRequest(old => ({tick:old.tick + 1,background:false})), []);
  const refresh = useCallback(() => setRequest(old => ({tick:old.tick + 1,background:true})), []);
  return { data, error, loading, refreshing: current && result.refreshing, reload, refresh, setData };
}

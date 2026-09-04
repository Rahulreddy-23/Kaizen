import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
  setData: (d: T) => void;
}

export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

/** Run an async loader whenever deps change. Keeps the previous data while reloading; ignores stale results. */
export function useAsync<T>(fn: () => Promise<T>, deps: DependencyList): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const seq = useRef(0);
  useEffect(() => {
    const id = ++seq.current;
    setLoading(true);
    setError(null);
    fn().then(
      (d) => {
        if (seq.current !== id) return;
        setData(d);
        setLoading(false);
      },
      (e) => {
        if (seq.current !== id) return;
        setError(errorMessage(e));
        setLoading(false);
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, setData };
}

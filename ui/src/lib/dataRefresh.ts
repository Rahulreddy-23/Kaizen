import { useEffect, useRef } from "react";

const EVENT = "kaizen:data-changed";
const STORAGE_KEY = "kaizen.dataChanged";
type Change = { runId?: string; nonce: string };

// One small change check per tab, shared by every mounted view. Full datasets
// are fetched only after a change, rather than by each view every 30 seconds.
const listeners = new Set<() => void>();
let stopPolling: (() => void) | undefined;

function subscribeChanges(listener: () => void) {
  listeners.add(listener);
  if (!stopPolling) {
    let active = true, pending = false, revision: string | undefined, denied = false;
    let controller: AbortController | undefined;
    const check = async () => {
      if (pending || document.visibilityState !== "visible") return;
      pending = true;
      controller = new AbortController();
      const timeout = window.setTimeout(() => controller?.abort(), 15000);
      try {
        const response = await fetch("/api/changes", {cache:"no-store",signal:controller.signal});
        if (!active) return;
        if (response.status === 401 || response.status === 403) {
          if (!denied) listeners.forEach(refresh => refresh());
          denied = true; revision = undefined; return;
        }
        if (!response.ok) return;
        const next = (await response.json()).revision;
        if (!active || typeof next !== "string") return;
        if (denied || (revision !== undefined && revision !== next)) listeners.forEach(refresh => refresh());
        revision = next; denied = false;
      } catch { /* Keep the current view on transient network failures. Focus retries. */ }
      finally { window.clearTimeout(timeout); pending = false; }
    };
    void check();
    const timer = window.setInterval(() => {void check();}, 5000);
    document.addEventListener("visibilitychange", check);
    stopPolling = () => {
      active = false; controller?.abort(); window.clearInterval(timer);
      document.removeEventListener("visibilitychange", check);
    };
  }
  return () => {
    listeners.delete(listener);
    if (!listeners.size) {stopPolling?.(); stopPolling = undefined;}
  };
}

/** Refresh read-only views after a successful mutation, including other browser tabs. */
export function notifyDataChanged(path: string) {
  if (typeof window === "undefined" || !path.startsWith("/api/runs")) return;
  const id = path.match(/^\/api\/runs\/([^/?]+)/)?.[1];
  const change: Change = { runId: id && !["upload", "from-path"].includes(id) ? decodeURIComponent(id) : undefined, nonce: `${Date.now()}-${Math.random()}` };
  window.dispatchEvent(new CustomEvent<Change>(EVENT, { detail: change }));
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(change)); } catch { /* Refresh on focus still works without storage. */ }
}

export function useDataRefresh(reload: () => void, runId?: string) {
  const reloadRef = useRef(reload);
  reloadRef.current = reload;
  useEffect(() => {
    const refresh = () => reloadRef.current();
    const changed = (change: Change) => { if (!runId || !change.runId || runId === change.runId) refresh(); };
    const event = (e: Event) => changed((e as CustomEvent<Change>).detail);
    const storage = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEY || !e.newValue) return;
      try { changed(JSON.parse(e.newValue) as Change); } catch { /* Ignore malformed browser storage. */ }
    };
    const visible = () => { if (document.visibilityState === "visible") refresh(); };
    const unsubscribe = subscribeChanges(visible);
    window.addEventListener(EVENT, event);
    window.addEventListener("storage", storage);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", visible);
    return () => {
      window.removeEventListener(EVENT, event);
      window.removeEventListener("storage", storage);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", visible);
      unsubscribe();
    };
  }, [runId]);
}

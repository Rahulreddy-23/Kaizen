// Toasts: acknowledgement that stays out of the way. Enter 200ms, exit 120ms (exits faster than
// entrances); transitions rather than keyframes so rapid toasts retarget smoothly.
import { CheckCircle, Info, Warning, XCircle } from "@phosphor-icons/react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

export type ToastTone = "ok" | "bad" | "warn" | "info";
export interface ToastInput {
  title: ReactNode;
  description?: ReactNode;
  tone?: ToastTone;
  /** ms; default 4200, errors 7000 */
  duration?: number;
}
interface ToastItem extends ToastInput {
  id: number;
  leaving: boolean;
}

const Ctx = createContext<{ toast: (t: ToastInput) => void } | null>(null);

export function useToast() {
  const c = useContext(Ctx);
  if (!c) throw new Error("ToastProvider is missing");
  return c.toast;
}

const ICON: Record<ToastTone, ReactNode> = {
  ok: <CheckCircle size={18} weight="fill" className="text-ok" />,
  bad: <XCircle size={18} weight="fill" className="text-bad" />,
  warn: <Warning size={18} weight="fill" className="text-warn" />,
  info: <Info size={18} weight="fill" className="text-brand-600" />,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const seq = useRef(0);
  const timers = useRef(new Map<number, number>());

  const dismiss = useCallback((id: number) => {
    setItems((xs) => xs.map((x) => (x.id === id ? { ...x, leaving: true } : x)));
    window.setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 140);
  }, []);

  const toast = useCallback(
    (t: ToastInput) => {
      const id = ++seq.current;
      setItems((xs) => [...xs.slice(-3), { ...t, id, leaving: false }]);
      const ms = t.duration ?? (t.tone === "bad" ? 7000 : 4200);
      timers.current.set(id, window.setTimeout(() => dismiss(id), ms));
    },
    [dismiss],
  );

  useEffect(() => {
    const t = timers.current;
    return () => t.forEach((h) => window.clearTimeout(h));
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);
  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 w-[22rem] max-w-[calc(100vw-2rem)]" aria-live="polite">
        {items.map((t) => (
          <div
            key={t.id}
            role="status"
            className="card shadow-pop px-3.5 py-3 flex items-start gap-2.5 transition-[opacity,transform] ease-out"
            style={{ transitionDuration: t.leaving ? "120ms" : "200ms", opacity: t.leaving ? 0 : 1, transform: t.leaving ? "translateY(6px) scale(0.98)" : "translateY(0) scale(1)" }}
          >
            <span className="mt-0.5 shrink-0">{ICON[t.tone ?? "info"]}</span>
            <div className="min-w-0 flex-1 text-sm">
              <div className="font-medium text-ink">{t.title}</div>
              {t.description && <div className="text-ink-3 mt-0.5">{t.description}</div>}
            </div>
            <button className="text-ink-3 hover:text-ink text-xs shrink-0" onClick={() => dismiss(t.id)} aria-label="Dismiss">
              ✕
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

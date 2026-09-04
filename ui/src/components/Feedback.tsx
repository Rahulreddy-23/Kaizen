import type { ReactNode } from "react";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="text-xs text-gray-500 py-3">{label}</div>;
}

export function ErrorBox({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="border border-red-700 bg-red-50 text-red-900 text-xs px-3 py-2 rounded-sm flex items-start gap-3">
      <span className="font-semibold shrink-0">Error</span>
      <span className="flex-1 break-words">{error}</span>
      {onRetry && (
        <button className="btn btn-sm" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Notice({ kind = "info", children }: { kind?: "info" | "good" | "warn" | "bad"; children: ReactNode }) {
  const cls = {
    info: "border-gray-400 bg-gray-50 text-gray-800",
    good: "border-green-700 bg-green-50 text-green-900",
    warn: "border-amber-600 bg-amber-50 text-amber-900",
    bad: "border-red-700 bg-red-50 text-red-900",
  }[kind];
  return <div className={`border text-xs px-3 py-2 rounded-sm ${cls}`}>{children}</div>;
}

export function ConfirmDialog({
  title,
  children,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
  busy = false,
}: {
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-40 bg-black/30 flex items-center justify-center" onClick={onCancel}>
      <div className="panel w-[30rem] max-w-[92vw] shadow-lg" onClick={(e) => e.stopPropagation()}>
        <div className="panel-title">{title}</div>
        <div className="p-3 text-xs space-y-2">{children}</div>
        <div className="px-3 py-2 border-t border-gray-200 flex justify-end gap-2">
          <button className="btn" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={onConfirm} disabled={busy}>
            {busy ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

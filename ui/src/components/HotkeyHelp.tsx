import { HOTKEYS } from "../lib/hotkeys";

/** Keyboard reference. Opened with "?"; closed with Esc, "?" or a click outside. */
export function HotkeyHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 bg-black/30 flex items-start justify-center pt-24" onClick={onClose} role="dialog" aria-label="Keyboard shortcuts">
      <div className="bg-white border border-gray-400 shadow-lg w-[28rem] max-w-[90vw] p-4 text-xs" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-baseline justify-between mb-2">
          <div className="font-semibold text-sm">Keyboard shortcuts</div>
          <button className="btn btn-sm" onClick={onClose}>
            Close (Esc)
          </button>
        </div>
        <table className="w-full">
          <tbody>
            {HOTKEYS.map(([key, what]) => (
              <tr key={key} className="border-t border-gray-200">
                <td className="py-1 pr-3 mono whitespace-nowrap align-top">{key}</td>
                <td className="py-1 text-gray-700">{what}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="text-2xs text-gray-500 mt-2">Shortcuts are ignored while you type in a field. Choosing a decision with a key does not submit it; Enter does.</div>
      </div>
    </div>
  );
}

export function HotkeyHint() {
  return (
    <span className="text-2xs text-gray-500" title="Keyboard shortcuts">
      keys: <span className="mono">j</span>/<span className="mono">k</span> move · <span className="mono">Enter</span> open/submit · <span className="mono">?</span> help
    </span>
  );
}

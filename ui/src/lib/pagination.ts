import { useState } from "react";

export function usePagedList<T>(items: T[], resetKey: string, size = 25, initialOffset = 0) {
  const [state, setState] = useState({ key: resetKey, offset: initialOffset });
  const last = Math.max(0, Math.floor((items.length - 1) / size) * size);
  const offset = state.key === resetKey ? Math.min(state.offset, last) : Math.min(initialOffset, last);
  return {
    rows: items.slice(offset, offset + size), offset, size, total: items.length,
    setOffset: (next: number) => setState({ key: resetKey, offset: Math.max(0, Math.min(last, next)) }),
  };
}

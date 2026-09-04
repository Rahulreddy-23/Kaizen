// Reviewer identity (name + slot + blind mode), persisted in localStorage. There is no authentication in
// this local tool; the name is recorded verbatim on every decision for the audit trail.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { ViewerParams } from "../types";

export interface ReviewerIdentity {
  name: string;
  slot: 1 | 2;
  blind: boolean;
}

const KEY = "kaizen.reviewer";
const DEFAULT: ReviewerIdentity = { name: "", slot: 1, blind: false };

function load(): ReviewerIdentity {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const p = JSON.parse(raw) as Partial<ReviewerIdentity>;
      return { name: String(p.name ?? ""), slot: p.slot === 2 ? 2 : 1, blind: Boolean(p.blind) };
    }
  } catch {
    /* ignore */
  }
  return DEFAULT;
}

interface Ctx {
  reviewer: ReviewerIdentity;
  setReviewer: (r: ReviewerIdentity) => void;
  /** Query parameters for result fetches: blind mode only applies to slot 2. */
  viewerParams: ViewerParams;
  /** Name used on API writes; empty when the reviewer has not identified themselves. */
  name: string;
}

const ReviewerContext = createContext<Ctx | null>(null);

export function ReviewerProvider({ children }: { children: ReactNode }) {
  const [reviewer, setReviewer] = useState<ReviewerIdentity>(load);
  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(reviewer));
    } catch {
      /* ignore */
    }
  }, [reviewer]);
  const value = useMemo<Ctx>(
    () => ({
      reviewer,
      setReviewer,
      viewerParams: { viewer: reviewer.slot, blind: reviewer.slot === 2 && reviewer.blind },
      name: reviewer.name.trim(),
    }),
    [reviewer],
  );
  return <ReviewerContext.Provider value={value}>{children}</ReviewerContext.Provider>;
}

export function useReviewer(): Ctx {
  const c = useContext(ReviewerContext);
  if (!c) throw new Error("ReviewerProvider is missing");
  return c;
}

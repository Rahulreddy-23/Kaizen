// The review-queue filter state lives in the URL query string so the evidence view can navigate
// prev/next within the same filtered set and the browser back button returns to the same page.
import type { ResultsQuery, ViewerParams } from "../types";

export const PAGE_SIZE = 100;

export const QUEUE_PARAM_KEYS = ["sku", "check", "discrepancy", "severity", "classification", "state", "role", "nv", "q", "offset"];

export function queueQueryFromParams(sp: URLSearchParams, v: ViewerParams, overrides: Partial<ResultsQuery> = {}): ResultsQuery {
  return {
    sku: sp.get("sku") || undefined,
    check: sp.get("check") || undefined,
    discrepancy: sp.get("discrepancy") || undefined,
    severity: sp.get("severity") || undefined,
    classification: sp.get("classification") || undefined,
    state: sp.get("state") || undefined,
    role: sp.get("role") || undefined,
    // Needs-validation filter is ON by default; "nv=0" shows every row.
    needs_validation: sp.get("nv") === "0" ? undefined : true,
    search: sp.get("q") || undefined,
    limit: PAGE_SIZE,
    offset: Math.max(0, Number(sp.get("offset") || 0) || 0),
    viewer: v.viewer,
    blind: v.blind || undefined,
    ...overrides,
  };
}

/** Only the queue-related params, so links stay short. */
export function queueParams(sp: URLSearchParams): URLSearchParams {
  const out = new URLSearchParams();
  for (const k of QUEUE_PARAM_KEYS) {
    const v = sp.get(k);
    if (v) out.set(k, v);
  }
  return out;
}

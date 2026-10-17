import { api } from "../api";
import type { ResultsQuery } from "../types";
import { PAGE_SIZE } from "./queue";

export interface Neighbor { id: string; offset: number }
export interface Neighbors { prev: Neighbor | null; next: Neighbor | null; index: number | null; total: number }

export async function loadNeighbors(runId: string, rowId: string, query: ResultsQuery): Promise<Neighbors> {
  let offset = query.offset ?? 0;
  let page = await api.getResults(runId, query);
  let index = page.rows.findIndex(row => row.row_id === rowId);
  // Direct links from Documents, Action items and Closed testing need not carry
  // a queue offset. Locate the row without discarding the current filters.
  if (index < 0) {
    for (let start = 0; start < page.total; start += PAGE_SIZE) {
      if (start === offset) continue;
      const candidate = await api.getResults(runId, {...query, offset: start, limit: PAGE_SIZE});
      const found = candidate.rows.findIndex(row => row.row_id === rowId);
      if (found >= 0) { page = candidate; offset = start; index = found; break; }
    }
  }
  if (index < 0) return {prev: null, next: null, index: null, total: page.total};
  let prev = index > 0 ? {id: page.rows[index - 1].row_id, offset} : null;
  let next = index + 1 < page.rows.length ? {id: page.rows[index + 1].row_id, offset} : null;
  if (!prev && offset > 0) {
    const before = await api.getResults(runId, {...query, offset: offset - 1, limit: 1});
    if (before.rows[0]) prev = {id: before.rows[0].row_id, offset: Math.max(0, offset - PAGE_SIZE)};
  }
  if (!next && offset + page.rows.length < page.total) {
    const after = await api.getResults(runId, {...query, offset: offset + page.rows.length, limit: 1});
    if (after.rows[0]) next = {id: after.rows[0].row_id, offset: offset + PAGE_SIZE};
  }
  return {prev, next, index: offset + index + 1, total: page.total};
}

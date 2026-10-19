import { describe, expect, it } from "vitest";
import { queueQueryFromParams, updateQueueFilter } from "./queue";

describe("queue pagination", () => {
  it("shows approved rows even when a link inherited Pending only", () => {
    expect(queueQueryFromParams(new URLSearchParams({state: "FINALIZED", nv: "1"}), {viewer: 1, blind: false}).needs_validation).toBeUndefined();
    const approved = updateQueueFilter(new URLSearchParams({nv: "1", offset: "100"}), "state", "FINALIZED");
    expect(approved.get("nv")).toBe("0");
    expect(approved.has("offset")).toBe(false);
    const pending = updateQueueFilter(approved, "nv", "");
    expect(pending.has("state")).toBe(false);
    expect(queueQueryFromParams(pending, {viewer: 1, blind: false}).needs_validation).toBe(true);
  });
  it("preserves engine and unresolved-finding links from the overview", () => {
    const query = queueQueryFromParams(new URLSearchParams({ nv: "0", engine_classification: "MISMATCH", unresolved: "1" }), { viewer: 1, blind: false });
    expect(query.engine_classification).toBe("MISMATCH");
    expect(query.unresolved).toBe(true);
    expect(query.needs_validation).toBeUndefined();
  });
  it.each(["-1", "0.5", "Infinity", "NaN", "9007199254740992"])("sanitizes malformed offset %s", offset => {
    expect(queueQueryFromParams(new URLSearchParams({ offset }), { viewer: 1, blind: false }).offset).toBe(0);
  });
});

// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("API error and upload behavior", () => {
  it("makes validation errors readable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: [{ loc: ["body", "name"], msg: "Input should be a valid string" }] }), { status: 422 })));
    await expect(api.listRuns()).rejects.toThrow("name: Input should be a valid string");
  });
  it("preserves a backend error reference", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Error reference: abc123" }), { status: 500 })));
    await expect(api.listRuns()).rejects.toThrow("Error reference: abc123");
  });
  it("does not send an unsupported selection", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    await expect(api.uploadRun([])).rejects.toBeInstanceOf(ApiError);
    await expect(api.uploadRun([{ name: "Kit", files: [new File(["PDF"], "only.pdf")] }])).rejects.toBeInstanceOf(ApiError);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("sends each folder's documents under that folder's unique name", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal("fetch", fetch);
    const files = () => ["one.pdf", "two.pdf", "three.pdf"].map(name => new File(["PDF"], name));
    await api.uploadRun([{ name: "Kit", files: files() }, { name: "Kit (2)", files: files() }], "My run");
    const form = fetch.mock.calls[0][1].body as FormData;
    expect(form.get("name")).toBe("My run");
    expect((form.getAll("files") as File[]).map(f => f.name)).toEqual(["Kit/one.pdf", "Kit/two.pdf", "Kit/three.pdf", "Kit (2)/one.pdf", "Kit (2)/two.pdf", "Kit (2)/three.pdf"]);
  });
});

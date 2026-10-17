// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("API error and upload behavior", () => {
  it("joins concurrent identical reads without retaining a response cache", async () => {
    let resolve!: (response: Response) => void;
    const fetch = vi.fn(() => new Promise<Response>(done => {resolve=done;}));
    vi.stubGlobal("fetch",fetch);
    const a = api.listRuns(), b = api.listRuns();
    expect(fetch).toHaveBeenCalledOnce();
    resolve(new Response('[]'));
    expect(await a).toEqual(await b);
    const next = api.listRuns();
    expect(fetch).toHaveBeenCalledTimes(2);
    resolve(new Response('[]')); await next;
  });
  it("never joins a read that started before sign-out", async () => {
    const pending: ((response:Response)=>void)[] = [];
    const fetch = vi.fn(() => new Promise<Response>(done => pending.push(done)));
    vi.stubGlobal("fetch",fetch);
    const old = api.listRuns();
    const logout = api.signOut();
    pending[1](new Response('{"ended":true}')); await logout;
    const next = api.listRuns();
    expect(fetch).toHaveBeenCalledTimes(3);
    pending[0](new Response('[]')); pending[2](new Response('[]'));
    await Promise.all([old,next]);
  });
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
    await expect(api.uploadRun([new File(["notes"], "notes.txt")])).rejects.toBeInstanceOf(ApiError);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("preserves relative folder paths and only sends supported files", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal("fetch", fetch);
    const pdf = new File(["PDF"], "bom.pdf");
    Object.defineProperty(pdf, "webkitRelativePath", { value: "Project/SKU/bom.pdf" });
    await api.uploadRun([pdf, new File(["notes"], "notes.txt")], "My run");
    const form = fetch.mock.calls[0][1].body as FormData;
    expect(form.get("name")).toBe("My run");
    expect(form.getAll("files")).toHaveLength(1);
    expect((form.get("files") as File).name).toBe("Project/SKU/bom.pdf");
  });
});

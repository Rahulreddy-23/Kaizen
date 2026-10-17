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
    await api.uploadRun([{ name: "Kit (2)", files: files() }], "My run");
    const form = fetch.mock.calls[0][1].body as FormData;
    expect(form.get("name")).toBe("My run");
    expect((form.getAll("files") as File[]).map(f => f.name)).toEqual(["Kit (2)/one.pdf", "Kit (2)/two.pdf", "Kit (2)/three.pdf"]);
  });
});

const stream = (chunks: string[]) => new Response(new ReadableStream({start(controller) {
  for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
  controller.close();
}}), {headers: {'content-type': 'application/x-ndjson'}});

it('reads progress and the result across arbitrary network chunk boundaries', async () => {
  const events = [{type: 'progress', percent: 0, stage: 'Preparing'}, {type: 'progress', percent: 70, stage: 'Comparing'}, {type: 'progress', percent: 100, stage: 'Complete'}, {type: 'result', data: {run_id: 'saved'}}].map(e => JSON.stringify(e)).join('\n');
  const fetch = vi.fn().mockResolvedValue(stream([events.slice(0, 13), events.slice(13, 99), events.slice(99)]));
  vi.stubGlobal('fetch', fetch);
  const progress = vi.fn();
  expect(await api.loadDemo(progress)).toEqual({run_id: 'saved'});
  expect(fetch.mock.calls[0][0]).toBe('/api/demo/load?stream=true');
  expect(progress.mock.calls.map(([p]) => p.percent)).toEqual([0, 70, 100]);
});

it('reports streamed server failures without pretending they completed', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(stream(['{"type":"progress","percent":5,"stage":"Reading"}\n{"type":"error","status":400,"detail":"Unreadable drawing"}\n'])));
  const progress = vi.fn();
  await expect(api.loadDemo(progress)).rejects.toThrow('Unreadable drawing');
  expect(progress.mock.calls.map(([p]) => p.percent)).toEqual([5]);
});

it('explains recovery if the stream ends without a result', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(stream(['{"type":"progress","percent":90,"stage":"Saving"}\n'])));
  await expect(api.loadDemo(vi.fn())).rejects.toThrow('Refresh All runs before retrying');
});

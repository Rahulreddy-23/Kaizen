// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { notifyDataChanged, useDataRefresh } from "./dataRefresh";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear(); });

describe("review data refresh", () => {
  it("refreshes matching runs and the run list after a successful approval", async () => {
    const matching = vi.fn(), other = vi.fn(), list = vi.fn();
    renderHook(() => useDataRefresh(matching, "first"));
    renderHook(() => useDataRefresh(other, "other"));
    renderHook(() => useDataRefresh(list));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response('{}')));
    await act(async () => { await api.finalize("first", { row_id: "row", final_decision: "ACCEPT", expected_revision: 1, confirm_self_approval: true }); });
    expect(matching).toHaveBeenCalledOnce();
    expect(list).toHaveBeenCalledOnce();
    expect(other).not.toHaveBeenCalled();
  });

  it("does not broadcast a rejected approval", async () => {
    const refresh = vi.fn();
    renderHook(() => useDataRefresh(refresh, "first"));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response('{"detail":"Row changed"}', { status: 409 })));
    await expect(api.finalize("first", { row_id: "row", final_decision: "ACCEPT", expected_revision: 1, confirm_self_approval: false })).rejects.toThrow("Row changed");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("receives changes from another tab and removes listeners on unmount", () => {
    const refresh = vi.fn();
    const { unmount } = renderHook(() => useDataRefresh(refresh, "first"));
    act(() => window.dispatchEvent(new StorageEvent("storage", { key: "kaizen.dataChanged", newValue: JSON.stringify({ runId: "first", nonce: "1" }) })));
    expect(refresh).toHaveBeenCalledOnce();
    unmount();
    notifyDataChanged("/api/runs/first/decisions");
    window.dispatchEvent(new Event("focus"));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("shares one lightweight poll, refreshes only on change, and stops when unmounted", async () => {
    vi.useFakeTimers();
    let revision = "one";
    const fetch = vi.fn(async () => new Response(JSON.stringify({revision})));
    vi.stubGlobal("fetch",fetch);
    const refresh = vi.fn(), second = vi.fn();
    const one = renderHook(() => useDataRefresh(refresh, "first"));
    const two = renderHook(() => useDataRefresh(second, "second"));
    await act(async () => {});
    expect(fetch).toHaveBeenCalledTimes(1);
    await act(async () => vi.advanceTimersByTimeAsync(5000));
    expect(refresh).not.toHaveBeenCalled();
    revision = "two";
    await act(async () => vi.advanceTimersByTimeAsync(5000));
    expect(refresh).toHaveBeenCalledOnce();
    expect(second).toHaveBeenCalledOnce();
    act(() => window.dispatchEvent(new Event("focus")));
    expect(refresh).toHaveBeenCalledTimes(2);
    one.unmount(); two.unmount();
    const before = fetch.mock.calls.length;
    await act(async () => vi.advanceTimersByTimeAsync(10000));
    expect(fetch).toHaveBeenCalledTimes(before);
  });

  it("does not overlap change checks or poll while hidden", async () => {
    vi.useFakeTimers();
    let resolve!: (response: Response) => void;
    const fetch = vi.fn(() => new Promise<Response>(done => {resolve=done;}));
    vi.stubGlobal("fetch",fetch);
    renderHook(() => useDataRefresh(vi.fn(),"first"));
    await act(async () => vi.advanceTimersByTimeAsync(10000));
    expect(fetch).toHaveBeenCalledOnce();
    await act(async () => resolve(new Response('{"revision":"one"}')));
    const visibility = vi.spyOn(document,"visibilityState","get").mockReturnValue("hidden");
    await act(async () => vi.advanceTimersByTimeAsync(10000));
    expect(fetch).toHaveBeenCalledOnce();
    visibility.mockRestore();
  });
});

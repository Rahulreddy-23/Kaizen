// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { ExcelExport } from "./ExcelExport";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("offers each rerun as a run version, newest first selected, for every workbook type", async () => {
  vi.spyOn(api, "runVersions").mockResolvedValue([
    { run_id: "orig", name: "Kit", created_at: "2026-11-01T10:00:00Z", rerun_number: 0 },
    { run_id: "r1", name: "Kit · Rerun 1", created_at: "2026-11-02T10:00:00Z", rerun_number: 1 },
    { run_id: "r2", name: "Kit · Rerun 2", created_at: "2026-11-03T10:00:00Z", rerun_number: 2 },
  ]);
  const openVersion = vi.fn();
  render(<ExcelExport runId="orig" onOpenVersion={openVersion} />);
  fireEvent.click(screen.getByRole("button", { name: "Download Excel" }));
  const select = await screen.findByLabelText("Run version") as HTMLSelectElement;
  expect([...select.options].map(o => o.text.split(" · ")[0])).toEqual(["Original run", "Rerun 1", "Rerun 2"]);
  expect(select.value).toBe("r2");
  expect(screen.getByRole("link", { name: "Download summary Excel" }).getAttribute("href")).toBe("/api/runs/r2/export.xlsx?detail=summary");
  fireEvent.change(select, { target: { value: "r1" } });
  expect(screen.getByRole("link", { name: "Download summary Excel" }).getAttribute("href")).toBe("/api/runs/r1/export.xlsx?detail=summary");
  expect(screen.getByRole("link", { name: "Download complete details Excel" }).getAttribute("href")).toBe("/api/runs/r1/export.xlsx?detail=complete");
  expect(screen.getByRole("link", { name: "Download BCC template Excel" }).getAttribute("href")).toBe("/api/runs/r1/export.xlsx?detail=bcc");
  fireEvent.click(screen.getByRole("button", { name: "Open selected version" }));
  expect(openVersion).toHaveBeenCalledWith("r1");
});

it("shows no version choice for a run that was never rerun", async () => {
  const versions = vi.spyOn(api, "runVersions").mockResolvedValue([{ run_id: "orig", name: "Kit", created_at: "2026-11-01T10:00:00Z", rerun_number: 0 }]);
  render(<ExcelExport runId="orig" />);
  fireEvent.click(screen.getByRole("button", { name: "Download Excel" }));
  await vi.waitFor(() => expect(versions).toHaveBeenCalled());
  expect(screen.queryByLabelText("Run version")).toBeNull();
});

describe("Excel download options", () => {
  it("offers explicit summary and complete downloads for this run", async () => {
    vi.spyOn(api, "runVersions").mockResolvedValue([]);
    render(<ExcelExport runId="run with spaces" />);
    const trigger = screen.getByRole("button", { name: "Download Excel" });
    fireEvent.click(trigger);
    const summary = await screen.findByRole("link", { name: "Download summary Excel" });
    const complete = screen.getByRole("link", { name: "Download complete details Excel" });
    expect(summary.getAttribute("href")).toBe("/api/runs/run%20with%20spaces/export.xlsx?detail=summary");
    expect(complete.getAttribute("href")).toBe("/api/runs/run%20with%20spaces/export.xlsx?detail=complete");
    const bcc = screen.getByRole("link", { name: "Download BCC template Excel" });
    expect(bcc.getAttribute("href")).toBe("/api/runs/run%20with%20spaces/export.xlsx?detail=bcc");
    expect(summary.hasAttribute("download")).toBe(true);
    expect(screen.getByText("One worksheet per SKU")).toBeTruthy();
    expect(document.activeElement).toBe(summary);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(summary, { key: "Escape" });
    expect(screen.queryByRole("region", { name: "Excel download options" })).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("dismisses on an outside click or when keyboard focus leaves", async () => {
    vi.spyOn(api, "runVersions").mockResolvedValue([]);
    render(<><ExcelExport runId="run" /><button>Outside</button></>);
    const trigger = screen.getByRole("button", { name: "Download Excel" });
    fireEvent.click(trigger);
    fireEvent.pointerDown(screen.getByRole("button", { name: "Outside" }));
    expect(screen.queryByRole("region", { name: "Excel download options" })).toBeNull();
    fireEvent.click(trigger);
    fireEvent.blur(await screen.findByRole("link", { name: "Download complete details Excel" }), { relatedTarget: screen.getByRole("button", { name: "Outside" }) });
    expect(screen.queryByRole("region", { name: "Excel download options" })).toBeNull();
  });

  it("waits for version data and retries a failed lookup without exporting the wrong run", async () => {
    vi.spyOn(api, "runVersions").mockRejectedValueOnce(new Error("Connection lost")).mockResolvedValueOnce([
      { run_id: "orig", name: "Kit", created_at: "2026-11-01T10:00:00Z", rerun_number: 0 },
      { run_id: "r1", name: "Kit · Rerun 1", created_at: "2026-11-02T10:00:00Z", rerun_number: 1 },
      { run_id: "r2", name: "Kit · Rerun 2", created_at: "2026-11-03T10:00:00Z", rerun_number: 2 },
    ]);
    render(<ExcelExport runId="r1" />);
    fireEvent.click(screen.getByRole("button", { name: "Download Excel" }));
    expect(screen.getByRole("status").textContent).toContain("Loading run versions");
    expect(screen.queryByRole("link", { name: "Download summary Excel" })).toBeNull();
    const retry = await screen.findByRole("button", { name: "Retry" });
    expect(screen.queryByRole("link", { name: "Download summary Excel" })).toBeNull();
    fireEvent.click(retry);
    const summary = await screen.findByRole("link", { name: "Download summary Excel" });
    expect(summary.getAttribute("href")).toBe("/api/runs/r1/export.xlsx?detail=summary");
  });
});

it('offers selected and all SKU comparisons independently of screen filters',()=>{
  render(<ExcelExport runId="run 1" quickSku="SKU/A"/>);
  fireEvent.click(screen.getByRole('button',{name:'Download Excel'}));
  expect(screen.getByRole('link',{name:'Download this SKU comparison Excel'}).getAttribute('href')).toBe('/api/runs/run%201/quick-view/export.xlsx?sku=SKU%2FA');
  expect(screen.getByRole('link',{name:'Download all SKUs comparison Excel'}).getAttribute('href')).toBe('/api/runs/run%201/quick-view/export.xlsx');
  expect(screen.getByText(/Screen filters are not applied/)).toBeTruthy();
});

// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ExcelExport } from "./ExcelExport";

afterEach(cleanup);

describe("Excel download options", () => {
  it("offers explicit summary and complete downloads for this run", () => {
    render(<ExcelExport runId="run with spaces" />);
    const trigger = screen.getByRole("button", { name: "Download Excel" });
    fireEvent.click(trigger);
    const summary = screen.getByRole("link", { name: "Download summary Excel" });
    const complete = screen.getByRole("link", { name: "Download complete details Excel" });
    expect(summary.getAttribute("href")).toBe("/api/runs/run%20with%20spaces/export.xlsx?detail=summary");
    expect(complete.getAttribute("href")).toBe("/api/runs/run%20with%20spaces/export.xlsx?detail=complete");
    expect(summary.hasAttribute("download")).toBe(true);
    expect(screen.getByText("One worksheet per SKU")).toBeTruthy();
    expect(document.activeElement).toBe(summary);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    fireEvent.keyDown(summary, { key: "Escape" });
    expect(screen.queryByRole("region", { name: "Excel download options" })).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });

  it("dismisses on an outside click or when keyboard focus leaves", () => {
    render(<><ExcelExport runId="run" /><button>Outside</button></>);
    const trigger = screen.getByRole("button", { name: "Download Excel" });
    fireEvent.click(trigger);
    fireEvent.pointerDown(screen.getByRole("button", { name: "Outside" }));
    expect(screen.queryByRole("region", { name: "Excel download options" })).toBeNull();
    fireEvent.click(trigger);
    fireEvent.blur(screen.getByRole("link", { name: "Download complete details Excel" }), { relatedTarget: screen.getByRole("button", { name: "Outside" }) });
    expect(screen.queryByRole("region", { name: "Excel download options" })).toBeNull();
  });
});

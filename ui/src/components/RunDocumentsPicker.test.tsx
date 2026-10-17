// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RunDocumentsPicker } from "./RunDocumentsPicker";

afterEach(cleanup);
const bom = new File(["bom"], "bom.xlsx");
Object.defineProperty(bom, "webkitRelativePath", { value: "Project/SKU-001/bom.xlsx" });
const label = new File(["label"], "label.pdf");
const handlers = () => ({ onSelect: vi.fn(), onRemove: vi.fn(), onClear: vi.fn() });

describe("run document selection", () => {
  it("opens the corresponding native folder and file pickers", () => {
    render(<RunDocumentsPicker files={[]} disabled={false} {...handlers()} />);
    const folder = screen.getByLabelText("Project folder");
    const individual = screen.getByLabelText("Individual documents");
    const folderClick = vi.spyOn(folder, "click");
    const filesClick = vi.spyOn(individual, "click");
    fireEvent.click(screen.getByRole("button", { name: "Choose folder" }));
    fireEvent.click(screen.getByRole("button", { name: "Choose files" }));
    expect(folderClick).toHaveBeenCalledOnce();
    expect(filesClick).toHaveBeenCalledOnce();
    expect(folder.hasAttribute("webkitdirectory")).toBe(true);
    expect(individual.getAttribute("accept")).toBe(".pdf,.xlsx,.xlsm,.csv");
  });

  it("retains the current selection when a picker is cancelled", () => {
    const callbacks = handlers();
    render(<RunDocumentsPicker files={[bom]} disabled={false} {...callbacks} />);
    fireEvent.change(screen.getByLabelText("Project folder"), { target: { files: [] } });
    expect(callbacks.onSelect).not.toHaveBeenCalled();
    expect(screen.getByText("bom.xlsx")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Individual documents"), { target: { files: [label] } });
    expect(callbacks.onSelect).toHaveBeenCalledWith([label]);
  });

  it("shows source paths and lets a reviewer remove individual files or clear all", () => {
    const callbacks = handlers();
    render(<RunDocumentsPicker files={[bom, label]} disabled={false} {...callbacks} />);
    expect(screen.getByRole("status").textContent).toContain("2 documents selected");
    expect(screen.getByText("Project/SKU-001")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Remove Project/SKU-001/bom.xlsx" }));
    expect(callbacks.onRemove).toHaveBeenCalledWith(0);
    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
    expect(callbacks.onClear).toHaveBeenCalledOnce();
  });

  it("locks selection controls while a run is starting", () => {
    const callbacks = handlers();
    render(<RunDocumentsPicker files={[bom]} disabled {...callbacks} />);
    for (const button of screen.getAllByRole("button")) {
      expect((button as HTMLButtonElement).disabled).toBe(true);
      fireEvent.click(button);
    }
    expect(callbacks.onRemove).not.toHaveBeenCalled();
    expect(callbacks.onClear).not.toHaveBeenCalled();
    expect((screen.getByLabelText("Project folder") as HTMLInputElement).disabled).toBe(true);
  });
});

// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { RunActions } from "./RunActions";
vi.mock("../api", () => ({api: {renameRun: vi.fn(), deleteRun: vi.fn()}}));
vi.mock("../lib/toast", () => ({useToast: () => vi.fn()}));
const run = {run_id: "run 1", name: "Alpha run", permission: "owner" as const};
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("run management", () => {
  it.each(["view", "edit"] as const)("does not offer owner actions to %s access", permission => {
    render(<RunActions run={{...run, permission}} />);
    expect(screen.queryByRole("button")).toBeNull();
  });
  it("validates and saves a trimmed name without changing run identity", async () => {
    vi.mocked(api.renameRun).mockResolvedValue({});
    const changed = vi.fn();
    render(<RunActions run={run} onChanged={changed} />);
    fireEvent.click(screen.getByRole("button", {name: "Options"}));
    fireEvent.click(screen.getByRole("menuitem", {name: "Rename run"}));
    const field = screen.getByRole("textbox", {name: "Run name"});
    expect((field as HTMLInputElement).maxLength).toBe(120);
    const save = screen.getByRole("button", {name: "Save name"}) as HTMLButtonElement;
    expect(save.disabled).toBe(true);
    fireEvent.change(field, {target: {value: "   "}});
    expect(save.disabled).toBe(true);
    fireEvent.change(field, {target: {value: "  Renamed project  "}});
    fireEvent.click(save);
    await waitFor(() => expect(changed).toHaveBeenCalledOnce());
    expect(api.renameRun).toHaveBeenCalledWith("run 1", "Renamed project");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
  it("requires a confirmation and supports cancelling deletion", () => {
    render(<RunActions run={run} />);
    fireEvent.click(screen.getByRole("button", {name: "Options"}));
    fireEvent.click(screen.getByRole("menuitem", {name: "Delete run"}));
    expect(screen.getByRole("dialog", {name: "Delete run?"})).toBeTruthy();
    expect(screen.getByText("Alpha run")).toBeTruthy();
    expect(api.deleteRun).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: "Cancel"}));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(api.deleteRun).not.toHaveBeenCalled();
  });
  it("keeps a failed delete available for retry and completes only the selected run", async () => {
    vi.mocked(api.deleteRun).mockRejectedValueOnce(new Error("Connection lost")).mockResolvedValueOnce({deleted:true});
    const deleted = vi.fn();
    render(<RunActions run={run} onDeleted={deleted} />);
    fireEvent.click(screen.getByRole("button", {name: "Options"}));
    fireEvent.click(screen.getByRole("menuitem", {name: "Delete run"}));
    fireEvent.click(screen.getByRole("button", {name: "Delete run"}));
    await screen.findByRole("alert");
    expect(deleted).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: "Delete run"}));
    await waitFor(() => expect(deleted).toHaveBeenCalledOnce());
    expect(api.deleteRun).toHaveBeenLastCalledWith("run 1");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

it('keeps owner actions inside Options with keyboard navigation and focus recovery', () => {
  render(<RunActions run={run}/>);
  const trigger=screen.getByRole('button',{name:'Options'});
  expect(screen.queryByRole('menuitem')).toBeNull();
  trigger.focus();fireEvent.keyDown(trigger,{key:'ArrowDown'});
  const rename=screen.getByRole('menuitem',{name:'Rename run'});
  const remove=screen.getByRole('menuitem',{name:'Delete run'});
  expect(document.activeElement).toBe(rename);
  fireEvent.keyDown(rename,{key:'ArrowDown'});expect(document.activeElement).toBe(remove);
  fireEvent.keyDown(remove,{key:'Escape'});expect(document.activeElement).toBe(trigger);
  expect(screen.queryByRole('menu')).toBeNull();
  fireEvent.click(trigger);fireEvent.click(screen.getByRole('menuitem',{name:'Rename run'}));
  fireEvent.click(screen.getByRole('button',{name:'Cancel'}));
  expect(document.activeElement).toBe(trigger);
  fireEvent.click(trigger);fireEvent.pointerDown(document.body);
  expect(screen.queryByRole('menu')).toBeNull();
});

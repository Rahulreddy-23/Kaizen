// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../api";
import { PermanentDeleteRun } from "./PermanentDeleteRun";

const toast = vi.hoisted(() => vi.fn());
vi.mock("../api", () => ({api: {permanentlyDeleteRun: vi.fn()}}));
vi.mock("../lib/toast", () => ({useToast: () => toast}));
const run = {run_id: "selected", name: "Alpha kit", permission: "owner" as const};
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

it.each(["view", "edit"] as const)("does not expose permanent deletion to %s collaborators", permission => {
  render(<PermanentDeleteRun run={{...run, permission}} onDeleted={vi.fn()}/>);
  expect(screen.queryByRole("button")).toBeNull();
});

it("requires explicit confirmation, supports cancelling and resets confirmation when reopened", () => {
  render(<PermanentDeleteRun run={run} onDeleted={vi.fn()}/>);
  fireEvent.click(screen.getByRole("button", {name: "Permanently delete Alpha kit"}));
  expect(screen.getByRole("dialog", {name: "Permanently delete this run?"})).toBeTruthy();
  expect(screen.getByText(/This cannot be undone/)).toBeTruthy();
  expect((screen.getByRole("button", {name: "Delete permanently"}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Type DELETE to confirm"), {target: {value: "DELETE"}});
  fireEvent.click(screen.getByRole("button", {name: "Keep run"}));
  expect(api.permanentlyDeleteRun).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", {name: "Permanently delete Alpha kit"}));
  expect((screen.getByLabelText("Type DELETE to confirm") as HTMLInputElement).value).toBe("");
});

it("locks the dialog during deletion and refreshes only on success", async () => {
  let finish!: (value: Awaited<ReturnType<typeof api.permanentlyDeleteRun>>) => void;
  vi.mocked(api.permanentlyDeleteRun).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const deleted = vi.fn();
  render(<PermanentDeleteRun run={run} onDeleted={deleted}/>);
  fireEvent.click(screen.getByRole("button", {name: "Permanently delete Alpha kit"}));
  fireEvent.change(screen.getByLabelText("Type DELETE to confirm"), {target: {value: "DELETE"}});
  fireEvent.click(screen.getByRole("button", {name: "Delete permanently"}));
  expect(api.permanentlyDeleteRun).toHaveBeenCalledWith("selected");
  expect((screen.getByRole("button", {name: "Close"}) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole("button", {name: "Keep run"}) as HTMLButtonElement).disabled).toBe(true);
  expect(deleted).not.toHaveBeenCalled();
  await act(async () => finish({deleted: true, cleanup_pending: false}));
  expect(deleted).toHaveBeenCalledOnce();
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("keeps a failed deletion open for retry and reports pending cleanup honestly", async () => {
  vi.mocked(api.permanentlyDeleteRun).mockRejectedValueOnce(new Error("This run is in use. Try again.")).mockResolvedValueOnce({deleted: true, cleanup_pending: true});
  const deleted = vi.fn();
  render(<PermanentDeleteRun run={run} onDeleted={deleted}/>);
  fireEvent.click(screen.getByRole("button", {name: "Permanently delete Alpha kit"}));
  fireEvent.change(screen.getByLabelText("Type DELETE to confirm"), {target: {value: "DELETE"}});
  fireEvent.click(screen.getByRole("button", {name: "Delete permanently"}));
  await screen.findByRole("alert");
  expect(deleted).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", {name: "Delete permanently"}));
  await waitFor(() => expect(deleted).toHaveBeenCalledOnce());
  expect(toast).toHaveBeenCalledWith(expect.objectContaining({tone: "warn", description: expect.stringContaining("cleanup is pending")}));
});

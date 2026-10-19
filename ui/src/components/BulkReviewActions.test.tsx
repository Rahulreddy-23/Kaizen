// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../api";
import { BulkReviewActions } from "./BulkReviewActions";

const toast = vi.hoisted(() => vi.fn());
vi.mock("../api", () => ({api: {bulkReviewPreview: vi.fn(), bulkApprove: vi.fn(), bulkAccept: vi.fn()}}));
vi.mock("../lib/toast", () => ({useToast: () => toast}));
afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.bulkReviewPreview).mockResolvedValue({accept_count: 2, approve_count: 3, revision: "first"});
});
function show(canEdit = true, approveOnly = false, onChanged = vi.fn()) {
  render(<MemoryRouter><BulkReviewActions runId="run" canEdit={canEdit} approveOnly={approveOnly} onChanged={onChanged}/></MemoryRouter>);
  return onChanged;
}

it("hides mutation controls from view-only collaborators", () => {
  show(false);
  expect(screen.queryByRole("button")).toBeNull();
});

it("requires explicit self-approval confirmation and locks controls until the approval finishes", async () => {
  let finish!: (value: {approved: number}) => void;
  vi.mocked(api.bulkApprove).mockImplementation(() => new Promise(resolve => {finish = resolve;}));
  const changed = show(true, true);
  fireEvent.click(screen.getByRole("button", {name: "Approve auto-cleared rows"}));
  const button = await screen.findByRole("button", {name: "Approve 3 rows"});
  expect((button as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("checkbox", {name: /I reviewed these pairings/}));
  fireEvent.click(button);
  expect(api.bulkApprove).toHaveBeenCalledWith("run", "first");
  expect((screen.getByRole("button", {name: "Close"}) as HTMLButtonElement).disabled).toBe(true);
  expect(changed).not.toHaveBeenCalled();
  await act(async () => finish({approved: 3}));
  expect(changed).toHaveBeenCalledOnce();
  expect(toast).toHaveBeenCalledWith(expect.objectContaining({title: "3 rows approved"}));
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("clearly distinguishes recording Accept decisions from approving rows", async () => {
  vi.mocked(api.bulkAccept).mockResolvedValue({accepted: 2});
  const changed = show();
  expect(screen.getByText("Bulk review")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", {name: "Bulk review"}));
  fireEvent.click(screen.getByRole("menuitem", {name: "Accept auto-cleared rows"}));
  const save = await screen.findByRole("button", {name: "Save 2 Accept decisions"});
  expect(screen.getByText(/Reviewed · awaiting approval/)).toBeTruthy();
  fireEvent.click(save);
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
  expect(api.bulkAccept).toHaveBeenCalledWith("run");
  expect(api.bulkApprove).not.toHaveBeenCalled();
  expect(toast).toHaveBeenCalledWith(expect.objectContaining({title: "2 Accept decisions saved"}));
});

it("requires a fresh preview and fresh confirmation after a stale or failed approval", async () => {
  vi.mocked(api.bulkApprove).mockRejectedValueOnce(new Error("These rows changed. Refresh the bulk preview before approving.")).mockResolvedValueOnce({approved: 1});
  const changed = show(true, true);
  fireEvent.click(screen.getByRole("button", {name: "Approve auto-cleared rows"}));
  await screen.findByRole("button", {name: "Approve 3 rows"});
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", {name: "Approve 3 rows"}));
  await screen.findByRole("alert");
  expect(changed).not.toHaveBeenCalled();
  vi.mocked(api.bulkReviewPreview).mockResolvedValueOnce({accept_count: 0, approve_count: 1, revision: "fresh"});
  fireEvent.click(screen.getByRole("button", {name: "Retry"}));
  const save = await screen.findByRole("button", {name: "Approve 1 row"});
  expect((save as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(save);
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
  expect(api.bulkApprove).toHaveBeenLastCalledWith("run", "fresh");
});

it("does not enable an empty approval or turn a failed preview into an approval", async () => {
  vi.mocked(api.bulkReviewPreview).mockResolvedValueOnce({accept_count: 0, approve_count: 0, revision: "empty"});
  show(true, true);
  fireEvent.click(screen.getByRole("button", {name: "Approve auto-cleared rows"}));
  await screen.findByText(/nothing to change/);
  fireEvent.click(screen.getByRole("checkbox"));
  expect((screen.getByRole("button", {name: "Approve 0 rows"}) as HTMLButtonElement).disabled).toBe(true);
  expect(api.bulkApprove).not.toHaveBeenCalled();
});

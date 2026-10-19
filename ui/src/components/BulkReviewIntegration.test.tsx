// @vitest-environment jsdom
import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {afterEach, expect, it, vi} from "vitest";
import {api} from "../api";
import {ToastProvider} from "../lib/toast";
import {BulkReviewActions} from "./BulkReviewActions";

vi.mock("../api", () => ({api: {bulkReviewPreview: vi.fn(), bulkApprove: vi.fn()}}));
afterEach(cleanup);

it("renders the approval receipt with the app's real toast provider outside the router", async () => {
  vi.mocked(api.bulkReviewPreview).mockResolvedValue({accept_count: 1, approve_count: 1, revision: "revision"});
  vi.mocked(api.bulkApprove).mockResolvedValue({approved: 1});
  const changed = vi.fn();
  render(<ToastProvider><MemoryRouter><BulkReviewActions runId="run" canEdit approveOnly onChanged={changed}/></MemoryRouter></ToastProvider>);
  fireEvent.click(screen.getByRole("button", {name: "Approve auto-cleared rows"}));
  await screen.findByRole("button", {name: "Approve 1 row"});
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", {name: "Approve 1 row"}));
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
  expect(screen.getByText("1 row approved")).toBeTruthy();
  expect(screen.getByRole("link", {name: "View approved rows"}).getAttribute("href")).toBe("#/runs/run/review?nv=0&state=FINALIZED");
  expect(screen.getByRole("button", {name: "Approve auto-cleared rows"})).toBeTruthy();
});

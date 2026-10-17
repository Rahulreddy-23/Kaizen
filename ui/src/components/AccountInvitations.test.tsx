// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "../api";
import { AccountInvitations } from "./AccountInvitations";
vi.mock("../api", () => ({api: {invitations: vi.fn(), invite: vi.fn(), revokeInvitation: vi.fn()}}));
afterEach(cleanup);
beforeEach(() => {vi.clearAllMocks(); vi.mocked(api.invitations).mockResolvedValue([]);});
it("creates a normalized email-bound invitation and only shows the returned code once", async () => {
  vi.mocked(api.invite).mockResolvedValue({id: "test", email: "person@bd.com", code: "synthetic-one-use-code", invited_by: "admin@bd.com", created_at: "2026-10-01", expires_at: "2099-10-03", consumed_at: "", revoked_at: ""});
  render(<AccountInvitations />);
  fireEvent.change(screen.getByRole("textbox", {name: "BD email address"}), {target: {value: "Person@BD.com"}});
  fireEvent.click(screen.getByRole("button", {name: "Create invitation"}));
  await screen.findByRole("textbox", {name: "Invitation code"});
  expect(api.invite).toHaveBeenCalledWith("person@bd.com");
  fireEvent.click(screen.getByRole("button", {name: "Hide code"}));
  expect(screen.queryByRole("textbox", {name: "Invitation code"})).toBeNull();
});
it("handles issuance failures without claiming an invitation was sent", async () => {
  vi.mocked(api.invite).mockRejectedValue(new Error("This account already exists."));
  render(<AccountInvitations />);
  fireEvent.change(screen.getByRole("textbox", {name: "BD email address"}), {target: {value: "existing@bd.com"}});
  fireEvent.click(screen.getByRole("button", {name: "Create invitation"}));
  await screen.findByRole("alert");
  expect(screen.queryByRole("textbox", {name: "Invitation code"})).toBeNull();
  expect((screen.getByRole("button", {name: "Create invitation"}) as HTMLButtonElement).disabled).toBe(false);
});
it("revokes a pending invitation", async () => {
  vi.mocked(api.invitations).mockResolvedValue([{id: "test", email: "person@bd.com", invited_by: "admin@bd.com", created_at: "2026-10-01", expires_at: "2099-10-03", consumed_at: "", revoked_at: ""}]);
  vi.mocked(api.revokeInvitation).mockResolvedValue({revoked: true});
  render(<AccountInvitations />);
  fireEvent.click(await screen.findByText("Pending invitations (1)"));
  fireEvent.click(screen.getByRole("button", {name: "Revoke invitation for person@bd.com"}));
  await waitFor(() => expect(api.revokeInvitation).toHaveBeenCalledWith("test"));
});

// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { api } from "../api";
import type { Relationship } from "../types";
import TerminologyPage from "./TerminologyPage";
vi.mock("../api", () => ({api: {terminology: {list: vi.fn(), select: vi.fn()}}}));
vi.mock("../lib/reviewer", () => ({useReviewer: () => ({name: "bob@bd.com", session: {is_admin: false}})}));
vi.mock("../lib/toast", () => ({useToast: () => vi.fn()}));
const term = (id: string, approved_by: string, extra: Partial<Relationship> = {}): Relationship => ({id, canonical: `Term ${id}`, aliases: [`Alias ${id}`], scope: "global", doc_types: [], item_anchors: [], provenance: "learned", created_by: approved_by, created_at: "2026-10-01", updated_at: "2026-10-01", active: true, notes: "", version: 2, approved_by, approved_at: "2026-10-01", enabled_version: null, selected_version: null, ...extra});
const terms = [term("A", "alice@bd.com"), term("B", "alice@bd.com"), term("C", "charlie@bd.com"), term("D", "", {is_default: true, enabled_version: 2})];
beforeEach(() => {vi.clearAllMocks(); vi.mocked(api.terminology.list).mockResolvedValue(terms); vi.mocked(api.terminology.select).mockResolvedValue({changed: 1});});
afterEach(cleanup);
const open = async () => {render(<MemoryRouter><TerminologyPage /></MemoryRouter>); await screen.findByRole("checkbox", {name: "Select Term A (A)"});};
it("adopts only explicitly selected entries, with their reviewed versions", async () => {
  await open();
  fireEvent.click(screen.getByRole("checkbox", {name: "Select Term A (A)"}));
  fireEvent.click(screen.getByRole("button", {name: "Add selected to my account"}));
  await waitFor(() => expect(api.terminology.select).toHaveBeenCalledWith([{id: "A", version: 2}], true));
  expect((screen.getByRole("checkbox", {name: "Select Term D (D)"}) as HTMLInputElement).disabled).toBe(true);
});
it("adopts a reviewer's entire filtered list without including another reviewer", async () => {
  await open();
  fireEvent.change(screen.getByRole("combobox", {name: "Approved by"}), {target: {value: "alice@bd.com"}});
  fireEvent.click(screen.getByRole("button", {name: "Add entire list"}));
  await waitFor(() => expect(api.terminology.select).toHaveBeenCalledWith([{id: "A", version: 2}, {id: "B", version: 2}], true));
});
it("keeps failed choices available for retry", async () => {
  vi.mocked(api.terminology.select).mockRejectedValueOnce(new Error("Terminology changed. Refresh the list."));
  await open();
  fireEvent.click(screen.getByRole("checkbox", {name: "Select Term B (B)"}));
  fireEvent.click(screen.getByRole("button", {name: "Add selected to my account"}));
  await screen.findByRole("alert");
  expect((screen.getByRole("checkbox", {name: "Select Term B (B)"}) as HTMLInputElement).checked).toBe(true);
  fireEvent.click(screen.getByRole("button", {name: "Add selected to my account"}));
  await waitFor(() => expect(api.terminology.select).toHaveBeenCalledTimes(2));
});
it("shows updates without silently choosing them and removes an inactive selection", async () => {
  vi.mocked(api.terminology.list).mockResolvedValue([term("A", "alice@bd.com", {selected_version: 1, enabled_version: 1}), term("B", "alice@bd.com", {selected_version: 2, active: false})]);
  await open();
  expect(screen.getByText(/v2 available/)).toBeTruthy();
  fireEvent.click(screen.getByRole("checkbox", {name: "Select Term B (B)"}));
  fireEvent.click(screen.getByRole("button", {name: "Remove selected from my account"}));
  await waitFor(() => expect(api.terminology.select).toHaveBeenCalledWith([{id: "B", version: 2}], false));
});

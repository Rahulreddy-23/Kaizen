// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AccountMenu } from "./AccountMenu";
const mocks = vi.hoisted(() => ({ signOut: vi.fn(), toast: vi.fn() }));
vi.mock("../lib/reviewer", () => ({useReviewer: () => ({session: {reviewer: "rahul.reddy@bd.com", is_admin: true}, signOut: mocks.signOut})}));
vi.mock("../lib/toast", () => ({useToast: () => mocks.toast}));
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  document.documentElement.dataset.theme = "light";
  vi.stubGlobal("matchMedia", vi.fn(() => ({matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn()})));
});
afterEach(() => {cleanup();vi.unstubAllGlobals();});
const show = () => render(<MemoryRouter><AccountMenu /><button>Outside</button></MemoryRouter>);

describe("account menu", () => {
  it("exposes only the avatar until opened, and supports menu keyboard navigation", () => {
    show();
    const trigger = screen.getByRole("button", {name: "Account menu"});
    expect(screen.queryByRole("menu")).toBeNull();
    fireEvent.keyDown(trigger, {key: "ArrowDown"});
    const profile = screen.getByRole("menuitem", {name: "Profile"});
    expect(profile.getAttribute("href")).toBe("/profile");
    expect(document.activeElement).toBe(profile);
    fireEvent.keyDown(profile, {key: "ArrowUp"});
    expect(document.activeElement).toBe(screen.getByRole("menuitem", {name: "Sign out"}));
    fireEvent.keyDown(document.activeElement!, {key: "Escape"});
    expect(screen.queryByRole("menu")).toBeNull();
    expect(document.activeElement).toBe(trigger);
  });
  it("switches appearance and closes the menu, remembering the choice", async () => {
    show();
    const trigger = screen.getByRole("button", {name: "Account menu"});
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("menuitem", {name: "Switch to dark mode"}));
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
    expect(localStorage.getItem("kaizen.theme")).toBe("dark");
    expect(screen.queryByRole("menu")).toBeNull();
    fireEvent.click(trigger);
    expect(screen.getByRole("menuitem", {name: "Switch to light mode"})).toBeTruthy();
  });
  it("dismisses outside clicks and keyboard focus leaving the menu", () => {
    show();
    const trigger = screen.getByRole("button", {name: "Account menu"});
    const outside = screen.getByRole("button", {name: "Outside"});
    fireEvent.click(trigger);
    fireEvent.pointerDown(outside);
    expect(screen.queryByRole("menu")).toBeNull();
    fireEvent.click(trigger);
    fireEvent.blur(screen.getByRole("menuitem", {name: "Profile"}), {relatedTarget: outside});
    expect(screen.queryByRole("menu")).toBeNull();
  });
  it("prevents duplicate sign-outs and reports errors for retry", async () => {
    let rejectSignOut!: (error: Error) => void;
    mocks.signOut.mockReturnValueOnce(new Promise((_resolve, reject) => { rejectSignOut = reject; }));
    show();
    fireEvent.click(screen.getByRole("button", {name: "Account menu"}));
    fireEvent.click(screen.getByRole("menuitem", {name: "Sign out"}));
    const pending = screen.getByRole("menuitem", {name: "Signing out…"}) as HTMLButtonElement;
    expect(pending.disabled).toBe(true);
    fireEvent.click(pending);
    expect(mocks.signOut).toHaveBeenCalledOnce();
    rejectSignOut(new Error("Connection lost"));
    await waitFor(() => expect(mocks.toast).toHaveBeenCalledWith({tone: "bad", title: "Couldn’t sign out", description: "Connection lost"}));
    expect((screen.getByRole("menuitem", {name: "Sign out"}) as HTMLButtonElement).disabled).toBe(false);
  });
});

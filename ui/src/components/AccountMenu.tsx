import { Moon, SignOut, Sun, UserCircle } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { displayName } from "../lib/format";
import { useReviewer } from "../lib/reviewer";
import { useToast } from "../lib/toast";
import { errorMessage } from "../lib/useAsync";
import { useTheme } from "./ThemeToggle";

export function AccountMenu() {
  const { session, signOut } = useReviewer();
  const [theme, toggleTheme] = useTheme();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const lastFirst = useRef(false);
  const id = useId();
  const items = () => Array.from(root.current?.querySelectorAll<HTMLElement>('[role="menuitem"]:not([disabled])') ?? []);
  const close = () => { setOpen(false); trigger.current?.focus(); };

  useEffect(() => {
    if (!open) return;
    const controls = items();
    (lastFirst.current ? controls[controls.length - 1] : controls[0])?.focus();
    const dismiss = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);

  if (!session) return null;
  const name = displayName(session.reviewer);
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map(word => word[0]?.toUpperCase()).join("");
  const endSession = async () => {
    setBusy(true);
    try { await signOut(); }
    catch (error) { toast({ tone: "bad", title: "Couldn’t sign out", description: errorMessage(error) }); }
    finally { setBusy(false); }
  };

  return <div ref={root} className="account-menu" onBlur={event => {
    if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget as Node)) setOpen(false);
  }} onKeyDown={event => {
    if (event.key === "Escape" && open) {
      event.preventDefault(); event.stopPropagation(); close();
    } else if (["ArrowDown", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      if (!open) { lastFirst.current = event.key === "ArrowUp"; setOpen(true); }
      else {
        const controls = items();
        const index = controls.indexOf(document.activeElement as HTMLElement);
        const next = index < 0 ? (event.key === "ArrowDown" ? 0 : controls.length - 1) : (index + (event.key === "ArrowDown" ? 1 : controls.length - 1)) % controls.length;
        controls[next]?.focus();
      }
    } else if (open && ["Home", "End"].includes(event.key)) {
      event.preventDefault();
      const controls = items();
      (event.key === "Home" ? controls[0] : controls[controls.length - 1])?.focus();
    } else if (open && event.key === "Tab") close();
  }}>
    <button ref={trigger} type="button" className="account-avatar" aria-label="Account menu" title="Account menu"
      aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined}
      onClick={() => { lastFirst.current = false; setOpen(value => !value); }}>{initials}</button>
    {open && <div id={id} className="account-menu-panel" role="menu" aria-label="Account options">
      <div className="account-menu-identity" role="presentation"><strong>{name}</strong><span>{session.is_admin ? "Administrator" : "Reviewer"}</span></div>
      <Link to="/profile" role="menuitem" tabIndex={-1} onClick={close}><UserCircle size={18} aria-hidden />Profile</Link>
      <button type="button" role="menuitem" tabIndex={-1} onClick={() => { toggleTheme(); close(); }}>
        {theme === "dark" ? <Sun size={18} aria-hidden /> : <Moon size={18} aria-hidden />}Switch to {theme === "dark" ? "light" : "dark"} mode
      </button>
      <button type="button" role="menuitem" tabIndex={-1} className="account-menu-signout" disabled={busy} onClick={() => void endSession()}>
        <SignOut size={18} aria-hidden />{busy ? "Signing out…" : "Sign out"}
      </button>
    </div>}
  </div>;
}

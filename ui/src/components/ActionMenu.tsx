import { CaretDown, DotsThree } from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Button } from "./ui";

/** Keyboard and pointer menu for infrequent actions. Dialogs live outside it. */
export function ActionMenu({ label = "Options", compact = false, items }: {
  label?: string; compact?: boolean;
  items: {label: string; icon: ReactNode; danger?: boolean; onSelect: () => void}[];
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const last = useRef(false);
  const id = useId();
  const controls = () => Array.from(root.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? []);
  const close = (restore = true) => {setOpen(false); if (restore) root.current?.querySelector<HTMLButtonElement>('[aria-haspopup="menu"]')?.focus();};
  useEffect(() => {
    if (!open) return;
    const buttons = controls();
    (last.current ? buttons[buttons.length - 1] : buttons[0])?.focus();
    const dismiss = (event: PointerEvent) => {if (!root.current?.contains(event.target as Node)) setOpen(false);};
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);
  return <div ref={root} className="action-menu" onBlur={event => {
    if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget as Node)) close(false);
  }} onKeyDown={event => {
    if (event.key === "Escape" && open) {event.preventDefault(); event.stopPropagation(); close();}
    else if (["ArrowDown", "ArrowUp"].includes(event.key)) {
      event.preventDefault();
      if (!open) {last.current = event.key === "ArrowUp"; setOpen(true);}
      else {const buttons = controls(); const index = buttons.indexOf(document.activeElement as HTMLButtonElement); buttons[(index + (event.key === "ArrowDown" ? 1 : buttons.length - 1)) % buttons.length]?.focus();}
    } else if (open && ["Home", "End"].includes(event.key)) {
      event.preventDefault(); const buttons = controls(); (event.key === "Home" ? buttons[0] : buttons[buttons.length - 1])?.focus();
    } else if (event.key === "Tab" && open) close();
  }}>
    <Button icon={compact ? <DotsThree size={20} weight="bold"/> : undefined} iconOnly={compact} iconRight={!compact ? <CaretDown size={14}/> : undefined} aria-label={label} title={label} aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined} onClick={() => {last.current = false; setOpen(value => !value);}}>{!compact && label}</Button>
    {open && <div id={id} className="action-menu-panel" role="menu" aria-label={label}>
      {items.map(item => <button key={item.label} role="menuitem" tabIndex={-1} type="button" className={item.danger ? "is-danger" : undefined} onClick={() => {close(); item.onSelect();}}>{item.icon}{item.label}</button>)}
    </div>}
  </div>;
}

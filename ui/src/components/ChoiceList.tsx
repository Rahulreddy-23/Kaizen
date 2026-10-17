import { MagnifyingGlass, X } from "@phosphor-icons/react";
import { useId, useMemo, useState } from "react";
import { Button } from "./ui";

export interface ChoiceOption {
  value: string;
  label: string;
  description?: string;
}

/** A searchable, keyboard-accessible list. Selection survives filtering. */
export function ChoiceList({ label, options, value, onChange, hint, disabled = false }: {
  label: string; options: ChoiceOption[]; value: string[]; onChange: (value: string[]) => void;
  hint?: string; disabled?: boolean;
}) {
  const id = useId();
  const [search, setSearch] = useState("");
  const selected = new Set(value);
  const labels = new Map(options.map(option => [option.value, option.label]));
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return options.filter(option => !query || `${option.label} ${option.description ?? ""} ${option.value}`.toLocaleLowerCase().includes(query));
  }, [options, search]);
  const toggle = (key: string) => onChange(selected.has(key) ? value.filter(item => item !== key) : [...value, key]);
  return <fieldset className="choice-list min-w-0" disabled={disabled} aria-describedby={hint ? `${id}-hint` : undefined}>
    <legend className="label">{label}</legend>
    <div className="choice-list-box">
      <div className="choice-list-toolbar">
        <span className="text-xs text-ink-3" aria-live="polite">{value.length ? `${value.length} selected` : "None selected"}</span>
        <Button size="sm" variant="ghost" disabled={!value.length} onClick={() => onChange([])} aria-label={`Clear ${label.toLowerCase()}`}>Clear selection</Button>
      </div>
      {!!value.length && <ul className="choice-list-selected" aria-label={`Selected ${label.toLowerCase()}`}>
        {value.map(key => <li key={key}><span>{labels.get(key) ?? key}</span><button type="button" onClick={() => toggle(key)} aria-label={`Remove ${labels.get(key) ?? key} from ${label.toLowerCase()}`}><X size={14} aria-hidden /></button></li>)}
      </ul>}
      <div className="choice-list-search">
        <MagnifyingGlass size={16} aria-hidden />
        <input type="search" id={`${id}-search`} value={search} onChange={event => setSearch(event.target.value)} aria-label={`Search ${label.toLowerCase()}`} placeholder="Search options…" />
      </div>
      <div className="choice-list-options" role="group" aria-label={`${label} options`} tabIndex={0}>
        {filtered.map(option => <label key={option.value} className={`choice-option ${selected.has(option.value) ? "is-selected" : ""}`}>
          <input type="checkbox" value={option.value} checked={selected.has(option.value)} onChange={() => toggle(option.value)} />
          <span><span className="choice-option-label">{option.label}</span>{option.description && <span className="choice-option-description">{option.description}</span>}</span>
        </label>)}
        {!filtered.length && <p className="px-3 py-4 text-sm text-ink-3">{options.length ? "No options match your search. Your selections are kept." : "No options available for this source."}</p>}
      </div>
      <div className="choice-list-count">{filtered.length} of {options.length} options</div>
    </div>
    {hint && <p id={`${id}-hint`} className="hint mt-1.5">{hint}</p>}
  </fieldset>;
}

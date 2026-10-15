import { CaretLeft, CaretRight } from "@phosphor-icons/react";
import { Button } from "./ui";

export function Pagination({ offset, size, total, onChange, label, loading = false }: {
  offset: number; size: number; total: number; onChange: (offset: number) => void; label: string; loading?: boolean;
}) {
  if (total <= size) return null;
  return <nav className="list-pagination" aria-label={`${label} pagination`}>
    <span aria-live="polite">{offset + 1}–{Math.min(offset + size, total)} of {total}</span>
    <div className="flex items-center gap-2">
      <Button size="sm" disabled={loading || offset === 0} onClick={() => onChange(Math.max(0, offset - size))} icon={<CaretLeft size={14} />} aria-label={`Previous ${label.toLowerCase()} page`}>Previous</Button>
      <Button size="sm" disabled={loading || offset + size >= total} onClick={() => onChange(offset + size)} iconRight={<CaretRight size={14} />} aria-label={`Next ${label.toLowerCase()} page`}>Next</Button>
    </div>
  </nav>;
}

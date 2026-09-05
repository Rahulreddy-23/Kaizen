"""Cross-check certificate: one A4 page per SKU.

It replaces the "checked by + date" stamp reviewers put on a marked-up BOM today, with the difference that
everything on it is verifiable: the run id, the SHA-256 of every input, the terminology version, the counts,
the named reviewers and their decisions, and the open action items. Nothing on the page is an opinion of
the tool; the engine's output is labelled as a recommendation and the decisions are the reviewers'.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf

from kaizen import __version__
from kaizen.models import Classification, Run
from kaizen.review.business import REVIEWABLE_ROLES

PAGE_W, PAGE_H = 595, 842  # A4 in points
MARGIN = 42
FONT = pymupdf.Font("helv")
FONT_BOLD = pymupdf.Font("hebo")
FONT_MONO = pymupdf.Font("cour")


@dataclass
class _Cursor:
    tw: pymupdf.TextWriter
    y: float = MARGIN

    def line(self, text: str, size: float = 9.5, font: pymupdf.Font = FONT, x: float = MARGIN, gap: float = 3.0) -> None:
        self.tw.append((x, self.y + size), text, font=font, fontsize=size)
        self.y += size + gap

    def wrapped(self, text: str, size: float = 9.0, width: int = 105, font: pymupdf.Font = FONT, x: float = MARGIN) -> None:
        for chunk in textwrap.wrap(text, width) or [""]:
            self.line(chunk, size, font, x)

    def heading(self, text: str) -> None:
        self.y += 5
        self.line(text.upper(), 8.5, FONT_BOLD, gap=4)

    def kv(self, key: str, value: str, size: float = 9.0) -> None:
        self.tw.append((MARGIN, self.y + size), key, font=FONT_BOLD, fontsize=size)
        self.tw.append((MARGIN + 150, self.y + size), value, font=FONT, fontsize=size)
        self.y += size + 3

    def space(self, n: float = 6) -> None:
        self.y += n


def _sku_rows(run: Run, sku: str):
    return [r for r in run.results if r.sku == sku]


def _reviewer_summary(rows, review) -> dict[str, Any]:
    """Who decided what on this SKU's rows. Empty when there are no decisions."""
    out: dict[str, Any] = {"slots": {1: {}, 2: {}}, "finalized": 0, "disagreements": 0, "blind": 0, "last": None}
    if review is None:
        return out
    ids = {r.row_id for r in rows}
    for row_id, slots in review.decisions.items():
        if row_id not in ids:
            continue
        for slot, d in slots.items():
            info = out["slots"].setdefault(slot, {})
            info.setdefault("names", set()).add(d.reviewer)
            info["count"] = info.get("count", 0) + 1
            info.setdefault("by_kind", {})[d.decision] = info.get("by_kind", {}).get(d.decision, 0) + 1
            if d.blind:
                out["blind"] += 1
            if out["last"] is None or d.decided_at > out["last"]:
                out["last"] = d.decided_at
        if review.states.get(row_id) == "DISAGREEMENT":
            out["disagreements"] += 1
    out["finalized"] = sum(1 for row_id in review.finals if row_id in ids)
    return out


def _draw_page(doc: pymupdf.Document, run: Run, sku: str, review, generated_at: str) -> None:
    group = next((g for g in run.groups if g.sku == sku), None)
    if group is None:
        raise ValueError(f"SKU {sku} is not in run {run.metadata.run_id}")
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    tw = pymupdf.TextWriter(page.rect)
    c = _Cursor(tw)
    m = run.metadata
    rows = _sku_rows(run, sku)
    rev = [r for r in rows if r.role in REVIEWABLE_ROLES]
    needs = sum(1 for r in rev if r.requires_validation)
    counts = {cl.value: sum(1 for r in rev if r.classification is cl) for cl in Classification}
    blockers = [r for r in rows for d in r.discrepancies if d.severity.value == "BLOCKER"]
    headers = [r for r in rows if r.role in ("header", "reference", "coverage")]

    # ---- title block
    c.line("CROSS-CHECK CERTIFICATE", 16, FONT_BOLD, gap=2)
    c.line(f"Kaizen Cross-Check v{m.tool_version} · BOM / label / drawing / PCO cross-check · generated {generated_at}", 8, gap=8)
    c.kv("SKU", f"{sku}    (product family {group.family})", 11)
    c.kv("Run", m.run_id)
    c.kv("Run timestamp", m.timestamp.isoformat(timespec="seconds"))
    c.kv("Terminology version", f"{m.terminology_version}  ({m.terminology_count} relationships)")
    c.kv("Thresholds", ", ".join(f"{k} {v}" for k, v in m.thresholds.model_dump().items()))

    # ---- documents
    c.heading("Documents compared (SHA-256 identifies each file exactly)")
    for d in run.documents:
        if d.id in group.document_ids:
            c.line(f"{d.doc_type.value:<8} {Path(d.path).name}   parser {d.parser_name} v{d.parser_version}   {len(d.items)} lines", 8.5)
            c.line(d.sha256, 7, FONT_MONO, x=MARGIN + 12, gap=4)
    if group.warnings:
        c.wrapped("Grouping notes: " + "; ".join(group.warnings), 8)

    # ---- engine results
    c.heading("Engine results for this SKU (recommendations, not decisions)")
    c.kv("Comparison rows", f"{len(rev)} reviewable  ({len(rows) - len(rev)} header, reference, coverage and exempt rows shown separately)")
    c.kv("By classification", "   ".join(f"{k} {v}" for k, v in counts.items()))
    c.kv("Needs validation", f"{needs}    auto-cleared {len(rev) - needs}")
    c.kv("Blockers", str(len(blockers)) if blockers else "none")
    for r in headers:
        flag = "OK" if not r.discrepancies else f"{r.discrepancies[0].type.value} ({r.discrepancies[0].severity.value})"
        c.wrapped(f"{r.role} · {r.check.value}: {flag} — {r.explanation}", 8, x=MARGIN + 12)

    # ---- reviewers
    c.heading("Reviewer decisions")
    summary = _reviewer_summary(rows, review)
    any_decisions = any(v.get("count") for v in summary["slots"].values())
    if not any_decisions:
        c.line("No reviewer decisions have been recorded for this SKU in the workspace.", 9)
    else:
        for slot, label in ((1, "Reviewer 1 (facilitator)"), (2, "Reviewer 2 (independent)")):
            info = summary["slots"].get(slot) or {}
            if not info.get("count"):
                c.kv(label, "no decisions recorded")
                continue
            kinds = ", ".join(f"{k} {v}" for k, v in sorted(info["by_kind"].items()))
            c.kv(label, f"{', '.join(sorted(info['names']))} — {info['count']} decision(s): {kinds}")
        c.kv("Finalized rows", str(summary["finalized"]))
        c.kv("Disagreements open", str(summary["disagreements"]))
        c.kv("Blind decisions", f"{summary['blind']} (reviewer 2 could not see reviewer 1 when deciding)")
        c.kv("Last decision", summary["last"] or "")

    # ---- action items
    c.heading("Action items")
    items = [a for a in (review.action_items if review else []) if a.sku == sku]
    open_items = [a for a in items if a.status not in ("RESOLVED", "CLOSED")]
    if not items:
        c.line("None raised for this SKU.", 9)
    else:
        c.kv("Open / total", f"{len(open_items)} / {len(items)}")
        for a in open_items[:8]:
            c.wrapped(f"{a.id} · {a.discrepancy_type} · {a.severity} · owner {a.owner or 'unassigned'} · {a.detail}", 8, x=MARGIN + 12)
        if len(open_items) > 8:
            c.line(f"... and {len(open_items) - 8} more open item(s) in the workbook", 8, x=MARGIN + 12)

    # ---- statement and signatures
    c.heading("Statement")
    c.wrapped(
        "The engine results above are a recommendation produced deterministically from the documents identified by the hashes on this page, "
        "the stated terminology version and thresholds. The decisions recorded were made by the named reviewers and are stored beside the "
        "recommendation, never over it. Re-running the same inputs with the same tool and terminology versions reproduces run "
        f"{m.run_id} and every row id on it. The reviewers decide; the tool does not approve anything.",
        8.5,
    )
    c.space(14)
    y = c.y
    for i, (label, slot) in enumerate((("Checked by (reviewer 1)", 1), ("Independent review (reviewer 2)", 2))):
        x = MARGIN + i * 260
        info = summary["slots"].get(slot) or {}
        name = ", ".join(sorted(info["names"])) if info.get("names") else ""
        tw.append((x, y + 9), label, font=FONT_BOLD, fontsize=8.5)
        tw.append((x, y + 24), name, font=FONT, fontsize=9.5)
        page.draw_line((x, y + 28), (x + 230, y + 28), width=0.6)
        tw.append((x, y + 38), f"date {summary['last'][:10] if summary['last'] and name else '____________'}", font=FONT, fontsize=8)
    tw.append((MARGIN, PAGE_H - MARGIN + 10), f"Kaizen Cross-Check v{__version__} · {m.run_id} · {sku} · page {len(doc)}", font=FONT, fontsize=7)
    tw.write_text(page)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_certificate(run: Run, sku: str, path: Path | str, review=None) -> Path:
    """One-page certificate for one SKU. `review` is a ReviewBundle (decisions, finals, states, action items)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    try:
        _draw_page(doc, run, sku, review, _now())
        doc.save(path, garbage=3, deflate=True)
    finally:
        doc.close()
    return path


def write_run_certificate(run: Run, path: Path | str, review=None) -> Path:
    """One page per SKU set in the run, in the run's group order."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    try:
        now = _now()
        for g in run.groups:
            _draw_page(doc, run, g.sku, review, now)
        doc.save(path, garbage=3, deflate=True)
    finally:
        doc.close()
    return path

"""Renders a synthetic product label PDF that mirrors the unit label in the brief: REF header, product name,
two-column 'Full Kit - Contents' list with wrapped lines, trademark paragraph, peel-off sub-labels repeating
the REF, LOT/expiry line, and bottom REF blocks. Built to break naive newline-based extraction."""

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from kaizen.datasets._stable import stabilize_pdf

PAGE_W, PAGE_H = 420, 640
FONT = "helv"
_FONT = pymupdf.Font(FONT)  # TextWriter path: Unicode-capable, renders ™ ® ° correctly (insert_text does not)
CONTENT_FONT = 6.5
CONTENT_STEP = 8.5
CONTINUATION_INDENT = 14
COLUMN_X = {1: [30], 2: [30, 220]}
COLUMN_WIDTH = {1: 360, 2: 172}


@dataclass
class LabelSpec:
    ref: str
    product_name: str
    contents: list[str] = field(default_factory=list)
    columns: int = 2
    contents_heading: str | None = "Full Kit - Contents:"
    brand: str = "PowerPICC SOLO2 Catheter"
    lot: str = "WWWWW0000"
    expiry: str = "2024-08-31"
    peel_offs: int = 4
    trademark_note: str = (
        "Bard, Flexura, MicroEZ, PowerPICC SOLO, Sherlock, Sherlock 3CG and StatLock are trademarks and/or "
        "registered trademarks of C. R. Bard, Inc. All other trademarks are the property of their respective owners."
    )
    storage_note: str = "Store between 20°C - 25°C (68°F - 77°F)."
    assembled: str = "Assembled In Mexico"
    artwork_code: str = "LABC726980"
    gtin: str = "00801741034596"
    extra_footer_lines: list[str] = field(default_factory=list)  # e.g. decoy 'REF 8888888' of a sub-component


def wrap(text: str, width: float, fontsize: float, indent: float = 0.0) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        candidate = f"{current} {w}".strip()
        avail = width - (indent if lines else 0)
        if current and _FONT.text_length(candidate, fontsize=fontsize) > avail:
            lines.append(current)
            current = w
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _balance(entries: list[list[str]], columns: int) -> list[list[list[str]]]:
    if columns == 1:
        return [entries]
    total = sum(len(e) for e in entries)
    cols: list[list[list[str]]] = [[], []]
    acc = 0
    for e in entries:
        if acc < total / 2:
            cols[0].append(e)
            acc += len(e)
        else:
            cols[1].append(e)
    return cols


def render_label_pdf(spec: LabelSpec, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    writer = pymupdf.TextWriter(page.rect)
    t = lambda x, y, s, size: writer.append((x, y), s, font=_FONT, fontsize=size)  # noqa: E731

    t(30, 38, spec.brand, 11)
    t(300, 38, "REF", 9)
    t(330, 38, spec.ref, 11)
    page.draw_line((30, 46), (390, 46), width=0.8)

    y = 68
    for line in wrap(spec.product_name, 250, 9):
        t(30, y, line, 9)
        y += 12

    if spec.contents_heading:
        y += 4
        t(30, y, spec.contents_heading, 7)
        page.draw_line((30, y + 3), (390, y + 3), width=0.5)
        y += 12
    cols = spec.columns if spec.columns in COLUMN_X else 2
    entries = [wrap(c, COLUMN_WIDTH[cols], CONTENT_FONT, CONTINUATION_INDENT) for c in spec.contents]
    y_end = y
    for col_idx, col_entries in enumerate(_balance(entries, cols)):
        x = COLUMN_X[cols][col_idx]
        yy = y
        for entry in col_entries:
            for i, line in enumerate(entry):
                t(x + (CONTINUATION_INDENT if i else 0), yy, line, CONTENT_FONT)
                yy += CONTENT_STEP
        y_end = max(y_end, yy)
    y = y_end + 16

    page.draw_line((30, y - 8), (390, y - 8), width=0.5)
    for line in wrap(spec.trademark_note, 360, 6):
        t(30, y, line, 6)
        y += 8
    t(30, y, spec.storage_note, 6)
    y += 16

    short_name = spec.product_name[:48]
    for i in range(spec.peel_offs):
        px = 30 + (i % 2) * 200
        py = y + (i // 2) * 42
        t(px, py, short_name, 5)
        t(px, py + 8, f"REF {spec.ref}", 5)
        t(px + 80, py + 8, f"(01){spec.gtin}", 5)
        t(px, py + 16, f"LOT {spec.lot}", 5)
        t(px + 80, py + 16, f"(17){spec.expiry.replace('-', '')[2:]}", 5)
        t(px, py + 24, spec.expiry, 5)
    y += 42 * ((spec.peel_offs + 1) // 2) + 8

    t(30, y, f"LOT {spec.lot}", 7)
    t(140, y, spec.expiry, 7)
    t(300, y, spec.assembled, 7)
    y += 12
    t(30, y, f"(01){spec.gtin}(17){spec.expiry.replace('-', '')[2:]}(10){spec.lot}", 5)
    t(300, y, f"(v5) {spec.artwork_code}", 6)
    y += 22

    for line in spec.extra_footer_lines:
        t(30, y, line, 6)
        y += 9
    for _ in range(2):
        t(30, y, "REF", 7)
        t(55, y, spec.ref, 8)
        yy = y
        for line in wrap(spec.product_name, 250, 7):
            t(120, yy, line, 7)
            yy += 9
        y = max(yy, y + 20) + 12

    writer.write_text(page)
    doc.set_metadata({"creationDate": "D:20260903000000", "modDate": "D:20260903000000", "producer": "Kaizen synthetic dataset", "creator": "Kaizen synthetic dataset"})
    doc.save(path)
    doc.close()
    stabilize_pdf(path)
    return path

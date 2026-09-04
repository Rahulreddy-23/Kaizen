"""Synthetic packaging drawings mirroring the tray drawing in the brief: EN/ES paired callouts with leader lines
around a tray outline, cavity labels, conditional callouts, notes block and a title block. Multi-sheet when there
are more callouts than one sheet holds. Vector text only (no raster) — a scanned drawing is out of scope."""

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from kaizen.datasets._stable import stabilize_pdf

_FONT = pymupdf.Font("helv")
PAGE_W, PAGE_H = 792, 612
TRAY = pymupdf.Rect(250, 110, 600, 400)
CALLOUT_FONT = 6.0
LINE_STEP = 7.2
SLOT_WIDTH = 165
LEFT_X, RIGHT_X = 40, 615
TOP_Y, BOTTOM_Y = 48, 418
CONDITIONAL_EN = "(IF APPLICABLE PER BOM)"
CONDITIONAL_ES = '(SI CORRESPONDE SEGUN EL BILLETE DE MATERIALES "BOM")'


@dataclass(frozen=True)
class CalloutSpec:
    en: str
    es: str
    conditional: bool = False
    placement: str | None = None  # e.g. "PLACE IN EITHER CAVITY #2 OR #3 OR #5"


@dataclass
class DrawingSpec:
    drawing_number: str
    revision: str
    title: str
    plant: str
    callouts: list[CalloutSpec] = field(default_factory=list)
    cavities: list[str] = field(default_factory=list)
    checked_by: str | None = None
    drawn_by: str = "W. McDONALD"
    drawn_date: str = "04-19-2011"
    checked_by_block: str = "E. VILLANUEVA"
    checked_date: str = "09-10-2024"
    size: str = "A"
    part_no: str = "N/A"


def _wrap(text: str, width: float, size: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if cur and _FONT.text_length(cand, fontsize=size) > width:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def _callout_lines(c: CalloutSpec) -> tuple[list[str], list[str]]:
    lines_en = _wrap(c.en, SLOT_WIDTH, CALLOUT_FONT)
    if c.placement:
        lines_en += _wrap(f"({c.placement})", SLOT_WIDTH, CALLOUT_FONT)
    if c.conditional:
        lines_en += _wrap(CONDITIONAL_EN, SLOT_WIDTH, CALLOUT_FONT)
    lines_es = _wrap(c.es, SLOT_WIDTH, CALLOUT_FONT)
    if c.placement:
        lines_es += _wrap("(COLOCAR EN CUALQUIERA DE LAS CAVIDADES INDICADAS)", SLOT_WIDTH, CALLOUT_FONT)
    if c.conditional:
        lines_es += _wrap(CONDITIONAL_ES, SLOT_WIDTH, CALLOUT_FONT)
    return lines_en, lines_es


def layout_sheets(callouts: list[CalloutSpec], column_bottom: float = 440.0, top: float = 60.0, gap: float = 22.0) -> list[list[tuple[CalloutSpec, float, float, str]]]:
    """Stack callouts down the left column then the right column; start a new sheet when both are full."""
    sheets: list[list[tuple[CalloutSpec, float, float, str]]] = [[]]
    col, y = 0, top
    for c in callouts:
        en, es = _callout_lines(c)
        height = (len(en) + len(es)) * LINE_STEP
        if y + height > column_bottom:
            col += 1
            y = top
            if col > 1:
                sheets.append([])
                col = 0
        x, side = (LEFT_X, "left") if col == 0 else (RIGHT_X, "right")
        sheets[-1].append((c, x, y, side))
        y += height + gap
    return sheets


def _draw_sheet(doc: pymupdf.Document, spec: DrawingSpec, callouts: list[tuple[CalloutSpec, float, float, str]], sheet: int, sheets: int) -> None:
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    w = pymupdf.TextWriter(page.rect)
    t = lambda x, y, s, size=CALLOUT_FONT: w.append((x, y), s, font=_FONT, fontsize=size)  # noqa: E731
    page.draw_rect(TRAY, width=1.2)
    page.draw_rect(pymupdf.Rect(TRAY.x0 + 10, TRAY.y0 + 10, TRAY.x1 - 10, TRAY.y1 - 10), width=0.4)
    for i, cav in enumerate(spec.cavities):
        cx, cy = TRAY.x0 + 40 + i * 110, TRAY.y0 + 30
        page.draw_rect(pymupdf.Rect(cx - 4, cy - 8, cx + 60, cy + 10), width=0.5)
        t(cx, cy, f"CAVITY #{cav}")
        t(cx, cy + 8, f"CAVIDAD #{cav}")
    for c, x, y, side in callouts:
        lines_en, lines_es = _callout_lines(c)
        yy = y
        for line in lines_en + lines_es:
            t(x, yy, line)
            yy += LINE_STEP
        if side == "left":
            start, end = (x + SLOT_WIDTH, y + 2), (TRAY.x0 + 30, min(max(y, TRAY.y0 + 20), TRAY.y1 - 20))
        elif side == "right":
            start, end = (x - 4, y + 2), (TRAY.x1 - 30, min(max(y, TRAY.y0 + 20), TRAY.y1 - 20))
        elif side == "top":
            start, end = (x + 40, y + 4), (x + 60, TRAY.y0 + 25)
        else:
            start, end = (x + 40, y - 6), (x + 60, TRAY.y1 - 25)
        page.draw_line(start, end, width=0.4)
        page.draw_circle(end, 1.6, width=0.4)
    # notes block
    ny = 470
    for line in ("NOTES: (UNLESS OTHERWISE SPECIFIED)", "1. FOR COMPONENTS PLACEMENT ONLY. REFER TO WORK ORDER", "   FOR COMPONENT APPLICABILITY AND QUANTITY.", "NOTAS: (A MENOS QUE SE ESPECIFIQUE LO CONTRARIO)", "1. PARA LA COLOCACION DE LOS COMPONENTES SOLAMENTE. VER", "   LA ORDEN DE TRABAJO PARA LA APLICABILIDAD Y CANTIDAD DEL COMPONENTE."):
        t(40, ny, line, 6.5)
        ny += 9
    # title block
    page.draw_rect(pymupdf.Rect(420, 455, 785, 600), width=0.8)
    page.draw_line((420, 520), (785, 520), width=0.5)
    page.draw_line((560, 455), (560, 600), width=0.5)
    t(425, 466, "TOLERANCES", 6.5)
    t(425, 475, "UNLESS OTHERWISE SPECIFIED:", 6)
    t(425, 486, "INCHES            mm", 6)
    t(425, 495, "X± .1             X±3", 6)
    t(425, 504, ".XX± .01          X.X±0.3", 6)
    t(425, 513, "ANGLES ± 1°   ALTERNATE UNITS ARE IN [ ]", 6)
    t(425, 532, f"DWN {spec.drawn_by}   DATE {spec.drawn_date}", 6)
    t(425, 542, f"CHK {spec.checked_by_block}   DATE {spec.checked_date}", 6)
    t(425, 560, "THIRD ANGLE PROJECTION", 6)
    t(565, 466, "UNLESS OTHERWISE SPECIFIED, ALL DIMENSIONS ARE IN INCHES.", 5.5)
    t(565, 474, "INTERPRET DRAWING PER ASME/ANSI Y14.5M.", 5.5)
    t(565, 482, "NOTICE: CONTAINS CONFIDENTIAL/PROPRIETARY INFORMATION AND", 5.5)
    t(565, 490, "UNAUTHORIZED REPRODUCTION OR DISCLOSURE STRICTLY PROHIBITED", 5.5)
    t(565, 505, "BD", 11)
    t(640, 505, spec.plant, 7)
    t(565, 532, "TITLE", 6)
    t(600, 532, spec.title, 8)
    t(565, 552, f"SIZE {spec.size}", 6)
    t(610, 552, f"PART NO. {spec.part_no}", 6)
    t(690, 552, "DRAWING NO.", 6)
    t(690, 562, spec.drawing_number, 8)
    t(760, 552, "REV.", 6)
    t(760, 562, spec.revision, 8)
    t(565, 578, "SCALE NONE", 6)
    t(620, 578, "DO NOT SCALE PRINT", 6)
    t(700, 578, f"SHEET {sheet} OF {sheets}", 6)
    if spec.checked_by:
        t(600, 445, f"Checked by {spec.checked_by}   {spec.checked_date}", 7)
    w.write_text(page)


def render_drawing_pdf(spec: DrawingSpec, path: Path | str, per_sheet: int = 20) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    sheets = layout_sheets(spec.callouts)
    for n, placed in enumerate(sheets, start=1):
        _draw_sheet(doc, spec, placed, n, len(sheets))
    doc.set_metadata({"creationDate": "D:20260903000000", "modDate": "D:20260903000000", "producer": "Kaizen synthetic dataset", "creator": "Kaizen synthetic dataset"})
    doc.save(path)
    doc.close()
    stabilize_pdf(path)
    return path

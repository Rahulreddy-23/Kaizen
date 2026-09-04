"""Renders a synthetic JDE 'Bill of Material Print' (report R30460) PDF that mirrors the layout in the brief.

Used for fixtures and the golden dataset. Layout facts that the parser relies on are the same ones a real
print exposes: header key/value lines, a two-line column header, one component per row.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from kaizen.datasets._stable import stabilize_pdf

PAGE_W, PAGE_H = 792, 612  # US letter landscape
FONT = "helv"
_FONT = pymupdf.Font(FONT)  # TextWriter path renders Unicode symbols correctly
ROW_FONT_SIZE = 7
HEADER_FONT_SIZE = 8
FIRST_ROW_Y = 172
ROW_STEP = 28

# x positions of column labels (points). Chosen to resemble the real report's proportions.
COLUMNS: list[tuple[str, str, float]] = [
    ("level", "Level", 30),
    ("component_item", "Component Item", 62),
    ("component_description", "Component Description", 150),
    ("branch_plant", "Branch/Plant", 352),
    ("quantity_per", "Quantity Per", 402),
    ("ext_qty", "Ext Qty", 462),
    ("um", "UM", 527),
    ("t", "T", 550),
    ("effective_from", "From", 566),
    ("effective_thru", "Thru", 616),
    ("oper_seq", "Seq No", 664),
    ("flags", "R", 706),
]
_COL_X = {name: x for name, _, x in COLUMNS}


@dataclass
class BomRowSpec:
    item: str
    description: str
    level: str = "1"
    branch: str = "5150"
    qty_per: str = "1.0000"
    ext_qty: str | None = None
    um: str = "EA"
    t: str = "P"
    eff_from: str = "12/11/09"
    eff_thru: str = "12/31/40"
    oper_seq: str = "5.00"
    flags: str = "N S S"


@dataclass
class AnnotationSpec:
    row_index: int
    field: str  # one of the column names in COLUMNS
    text: str


@dataclass
class BomSpec:
    parent_item: str
    parent_description: str
    rows: list[BomRowSpec] = field(default_factory=list)
    branch_plant: str = "5150"
    batch_qty: str = ""
    batch_uom: str = "EA"
    requested_qty: str = "1.0000"
    requested_uom: str = "EA"
    bill_type: str = "M"
    bill_revision: str = ""
    as_of_date: str = "09/03/25"
    report_id: str = "R30460"
    company: str = "C.R. Bard, Inc."
    print_date: str = "09/03/25"
    print_time: str = "6:38:16"
    annotations: list[AnnotationSpec] = field(default_factory=list)


def _draw_page_header(page: pymupdf.Page, writer: pymupdf.TextWriter, spec: BomSpec, page_no: int) -> None:
    t = lambda x, y, s, size=HEADER_FONT_SIZE: writer.append((x, y), s, font=_FONT, fontsize=size)  # noqa: E731
    t(30, 40, spec.report_id)
    t(330, 40, spec.company)
    t(640, 40, f"Date - {spec.print_date}")
    t(330, 52, "Bill of Material Print")
    t(640, 52, f"Time - {spec.print_time}")
    t(30, 64, f"As of Date {spec.as_of_date}")
    t(640, 64, f"Page - {page_no}")
    t(30, 92, f"Parent Item {spec.parent_item}")
    t(200, 92, f"Parent Description {spec.parent_description}")
    t(450, 92, f"Branch/Plant {spec.branch_plant}")
    t(620, 92, f"Type {spec.bill_type}")
    t(30, 104, f"Batch Quantity {spec.batch_qty}".rstrip())
    t(200, 104, f"Batch UOM {spec.batch_uom}")
    t(450, 104, f"Requested Quantity {spec.requested_qty}")
    t(620, 104, f"Requested UOM {spec.requested_uom}")
    t(30, 116, f"Bill Revision Level {spec.bill_revision}".rstrip())
    # two-line column header
    t(566, 140, "Effective", ROW_FONT_SIZE)
    t(664, 140, "Oper", ROW_FONT_SIZE)
    t(722, 140, "O", ROW_FONT_SIZE)
    t(738, 140, "Lk", ROW_FONT_SIZE)
    for _, label, x in COLUMNS:
        t(x, 152, label, ROW_FONT_SIZE)
    t(722, 152, "P", ROW_FONT_SIZE)
    t(738, 152, "Ty", ROW_FONT_SIZE)
    t(754, 152, "ST", ROW_FONT_SIZE)
    page.draw_line((30, 156), (770, 156), width=0.5)


def _draw_row(writer: pymupdf.TextWriter, row: BomRowSpec, y: float) -> None:
    t = lambda x, s: writer.append((x, y), s, font=_FONT, fontsize=ROW_FONT_SIZE)  # noqa: E731
    t(_COL_X["level"], row.level)
    t(_COL_X["component_item"], row.item)
    t(_COL_X["component_description"], row.description)
    t(_COL_X["branch_plant"], row.branch)
    t(_COL_X["quantity_per"], row.qty_per)
    t(_COL_X["ext_qty"], row.ext_qty if row.ext_qty is not None else f"{float(row.qty_per):.6f}" if _is_number(row.qty_per) else "")
    t(_COL_X["um"], row.um)
    t(_COL_X["t"], row.t)
    t(_COL_X["effective_from"], row.eff_from)
    t(_COL_X["effective_thru"], row.eff_thru)
    t(_COL_X["oper_seq"], row.oper_seq)
    t(_COL_X["flags"], row.flags)


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def render_bom_pdf(spec: BomSpec, path: Path | str, rows_per_page: int = 12) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    pages: list[pymupdf.Page] = []
    row_positions: dict[int, tuple[int, float]] = {}
    for start in range(0, max(len(spec.rows), 1), rows_per_page):
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        pages.append(page)
        writer = pymupdf.TextWriter(page.rect)
        _draw_page_header(page, writer, spec, len(pages))
        for i, row in enumerate(spec.rows[start : start + rows_per_page]):
            y = FIRST_ROW_Y + i * ROW_STEP
            _draw_row(writer, row, y)
            row_positions[start + i] = (len(pages) - 1, y)
        writer.write_text(page)
    for ann in spec.annotations:
        page_idx, y = row_positions[ann.row_index]
        x = _COL_X[ann.field]
        rect = pymupdf.Rect(x, y + 2, x + 70, y + 12)
        page = doc[page_idx]  # re-fetch: Page objects go stale once further pages have been created
        a = page.add_freetext_annot(rect, ann.text, fontsize=7, text_color=(0.85, 0.1, 0.1))
        a.update()
    doc.set_metadata({"creationDate": "D:20260903000000", "modDate": "D:20260903000000", "producer": "Kaizen synthetic dataset", "creator": "Kaizen synthetic dataset"})
    doc.save(path)
    doc.close()
    stabilize_pdf(path)
    return path

"""Synthetic PCO documents in the FM00835 'Bill of Material and Routing Form' layout from the brief (XLSX and PDF)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import pymupdf

from kaizen.datasets._stable import stabilize_pdf, stabilize_zip

HEADER_1 = ["Affected Codes", "Item Number", "Item Number", "Description", "Quantity", "Quantity", "Oper Seq#", "Oper Seq#", "Percent Scrap", "Percent Scrap"]
HEADER_2 = ["", "Actual", "Proposed", "", "Actual", "Proposed", "Actual", "Proposed", "Actual", "Proposed"]
XLSX_HEADER = ["Affected Codes", "Item Number Actual", "Item Number Proposed", "Description", "Quantity Actual", "Quantity Proposed", "Oper Seq# Actual", "Oper Seq# Proposed", "Percent Scrap Actual", "Percent Scrap Proposed"]
_FONT = pymupdf.Font("helv")
COL_X = [30, 118, 198, 282, 470, 520, 575, 628, 682, 738]
FIXED_TIME = datetime(2026, 9, 3, tzinfo=timezone.utc)


@dataclass
class PcoRowSpec:
    item_actual: str = ""
    item_proposed: str = ""
    description: str = ""
    qty_actual: str = ""
    qty_proposed: str = ""
    seq_actual: str = ""
    seq_proposed: str = ""
    scrap_actual: str = ""
    scrap_proposed: str = ""

    def cells(self) -> list[str]:
        return [self.item_actual, self.item_proposed, self.description, self.qty_actual, self.qty_proposed, self.seq_actual, self.seq_proposed, self.scrap_actual, self.scrap_proposed]


@dataclass
class PcoSpec:
    pco_number: str
    revision: str
    branch: str
    affected_codes: list[str] = field(default_factory=list)
    rows: list[PcoRowSpec] = field(default_factory=list)
    change_type: str = "Change"  # New | Change | Substitute
    bill_type: str = "M"  # M | ALT
    form: str = "FM00835"
    form_revision: str = "9"


def _box(flag: bool) -> str:
    return "[X]" if flag else "[ ]"


def write_pco_xlsx(spec: PcoSpec, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    wb.properties.created = wb.properties.modified = FIXED_TIME
    wb.properties.creator = wb.properties.lastModifiedBy = "Kaizen synthetic dataset"
    ws = wb.active
    ws.title = "PCO"
    ws.append([f"Always confirm use of the current revision of this document. {spec.pco_number}, {spec.revision}"])
    ws.append(["BD", None, "Bill of Material and Routing Form", None, None, spec.form])
    ws.append([None, None, "Billete de Materiales y Rutas Forma", None, None, f"Revision {spec.form_revision}"])
    ws.append(["If N/A remove this worksheet"])
    ws.append([f"{_box(spec.change_type == 'New')} New"])
    ws.append([f"{_box(spec.change_type == 'Change')} Change", None, None, None, None, f"Branch: {spec.branch}"])
    ws.append([f"{_box(spec.change_type == 'Substitute')} Substitute"])
    ws.append(["Type of Bill"])
    ws.append([f"{_box(spec.bill_type == 'M')} M"])
    ws.append([f"{_box(spec.bill_type == 'ALT')} ALT"])
    ws.append(["Bill of Materials (JDE) / Billete de Materiales (JDE)"])
    ws.append(XLSX_HEADER)
    n = max(len(spec.affected_codes), len(spec.rows))
    for i in range(n):
        code = spec.affected_codes[i] if i < len(spec.affected_codes) else ""
        cells = spec.rows[i].cells() if i < len(spec.rows) else [""] * 9
        ws.append([code, *cells])
    wb.save(path)
    stabilize_zip(path)
    return path


def render_pco_pdf(spec: PcoSpec, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    page = doc.new_page(width=792, height=612)
    w = pymupdf.TextWriter(page.rect)
    t = lambda x, y, s, size=7: w.append((x, y), s, font=_FONT, fontsize=size)  # noqa: E731
    t(230, 30, f"Always confirm use of the current revision of this document. {spec.pco_number}, {spec.revision}", 8)
    t(30, 60, "BD", 12)
    t(330, 60, "Bill of Material and Routing Form", 9)
    t(700, 60, spec.form, 8)
    t(330, 72, "Billete de Materiales y Rutas Forma", 8)
    t(700, 72, f"Revision {spec.form_revision}", 8)
    t(700, 84, "Page 1 of 1", 8)
    t(30, 96, "If N/A remove this worksheet", 7)
    t(30, 108, f"{_box(spec.change_type == 'New')} New")
    t(30, 118, f"{_box(spec.change_type == 'Change')} Change")
    t(700, 118, f"Branch: {spec.branch}", 8)
    t(30, 128, f"{_box(spec.change_type == 'Substitute')} Substitute")
    t(30, 146, "Type of Bill", 7)
    t(30, 156, f"{_box(spec.bill_type == 'M')} M")
    t(30, 166, f"{_box(spec.bill_type == 'ALT')} ALT")
    t(300, 186, "Bill of Materials (JDE) / Billete de Materiales (JDE)", 8)
    y1, y2 = 206, 216
    for x, h1, h2 in zip(COL_X, HEADER_1, HEADER_2):
        t(x, y1, h1)
        if h2:
            t(x, y2, h2)
    page.draw_line((28, 221), (790, 221), width=0.6)
    y = 234
    n = max(len(spec.affected_codes), len(spec.rows))
    for i in range(n):
        code = spec.affected_codes[i] if i < len(spec.affected_codes) else ""
        cells = spec.rows[i].cells() if i < len(spec.rows) else [""] * 9
        for x, text in zip(COL_X, [code, *cells]):
            if text:
                t(x, y, text)
        page.draw_line((28, y + 4), (790, y + 4), width=0.3)
        y += 13
    w.write_text(page)
    doc.set_metadata({"creationDate": "D:20260903000000", "modDate": "D:20260903000000", "producer": "Kaizen synthetic dataset", "creator": "Kaizen synthetic dataset"})
    doc.save(path)
    doc.close()
    stabilize_pdf(path)
    return path

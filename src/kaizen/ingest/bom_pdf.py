"""Parser for JDE 'Bill of Material Print' (R30460-style) PDFs.

Strategy: locate the column-header line by its labels, derive column x-bands from the label positions, group
words into visual lines, and read one component per line. Header key/values come from the lines above the
column header. FreeText annotations overlapping a row are captured as redlines (field + text).
"""

import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pymupdf

from kaizen.ingest.bom_categorize import CATEGORIZER_VERSION, categorize
from kaizen.ingest.hashing import document_id, sha256_file
from kaizen.ingest.pdf_words import ColumnBand, Word, assign_columns, extract_annotations, extract_words, group_lines, line_bbox, line_text
from kaizen.ingest.quantity import parse_decimal
from kaizen.models import DocType, Document, DocumentItem, Evidence

PARSER_NAME = "bom_pdf"
PARSER_VERSION = f"1+cat{CATEGORIZER_VERSION}"

# Column labels in left-to-right order, as token sequences.
HEADER_LABELS: list[tuple[str, tuple[str, ...]]] = [
    ("level", ("Level",)),
    ("component_item", ("Component", "Item")),
    ("component_description", ("Component", "Description")),
    ("branch_plant", ("Branch/Plant",)),
    ("quantity_per", ("Quantity", "Per")),
    ("ext_qty", ("Ext", "Qty")),
    ("um", ("UM",)),
    ("t", ("T",)),
    ("effective_from", ("From",)),
    ("effective_thru", ("Thru",)),
    ("oper_seq", ("Seq", "No")),
    ("flags", ("R",)),
]
_HEADER_PATTERNS = {
    "parent_item": re.compile(r"Parent Item\s+(\S+)"),
    "parent_description": re.compile(r"Parent Description\s+(.*?)\s+Branch/Plant"),
    "branch_plant": re.compile(r"Branch/Plant\s+(\S+)"),
    "type": re.compile(r"\bType\s+(\S+)"),
    "batch_quantity": re.compile(r"Batch Quantity\s+((?!Batch)\S+)"),
    "batch_uom": re.compile(r"Batch UOM\s+(\S+)"),
    "requested_quantity": re.compile(r"Requested Quantity\s+(\S+)"),
    "requested_uom": re.compile(r"Requested UOM\s+(\S+)"),
    "bill_revision_level": re.compile(r"Bill Revision Level\s+(\S+)"),
    "as_of_date": re.compile(r"As of Date\s+(\S+)"),
    "report_id": re.compile(r"^(R\d{5})\b"),
}
_ITEM_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-]*$")


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _find_header_line(lines: list[list[Word]]) -> tuple[int, list[ColumnBand]] | None:
    for idx, line in enumerate(lines):
        text = line_text(line)
        if "Component Item" in text and "Component Description" in text:
            return idx, _bands_from_header(line)
    return None


def _bands_from_header(line: list[Word], page_width: float = 10_000) -> list[ColumnBand]:
    words = sorted(line, key=lambda w: w.x0)
    starts: list[tuple[str, float]] = []
    pos = 0
    for name, tokens in HEADER_LABELS:
        n = len(tokens)
        found = None
        for i in range(pos, len(words) - n + 1):
            if tuple(w.text for w in words[i : i + n]) == tokens:
                found = i
                break
        if found is None:
            continue
        starts.append((name, words[found].x0))
        pos = found + n
    bands: list[ColumnBand] = []
    for i, (name, x0) in enumerate(starts):
        x1 = starts[i + 1][1] - 2 if i + 1 < len(starts) else page_width
        bands.append(ColumnBand(name, x0 - 2, x1))
    return bands


def _text(cols: dict[str, list[Word]], name: str) -> str:
    return " ".join(w.text for w in cols.get(name, []))


def parse_bom_pdf(path: Path | str) -> Document:
    path = Path(path)
    sha = sha256_file(path)
    doc_id = document_id("bom", sha, path)
    pdf = pymupdf.open(path)
    header: dict[str, str] = {}
    items: list[DocumentItem] = []
    warnings: list[str] = []
    row_counter = 0
    for page in pdf:
        page_no = page.number + 1
        words = extract_words(page)
        if not words and page.get_images(full=True):
            warnings.append(f"page {page_no}: image-only page (scanned BOM?); OCR for BOM prints is NOT IMPLEMENTED — page skipped")
            continue
        lines = group_lines(words)
        found = _find_header_line(lines)
        if found is None:
            warnings.append(f"page {page_no}: column header not found; page skipped")
            continue
        header_idx, bands = found
        if not header:
            _parse_header(lines[:header_idx], header)
        as_of = _parse_date(header.get("as_of_date"))
        annots = extract_annotations(page)
        for line in lines[header_idx + 1 :]:
            cols = assign_columns(line, bands)
            item_number = _text(cols, "component_item")
            level = _text(cols, "level")
            if not item_number or not _ITEM_RE.match(item_number) or not level.isdigit():
                continue
            row_counter += 1
            description = _text(cols, "component_description")
            qty_text = _text(cols, "quantity_per")
            quantity: Decimal | None
            confidence = 1.0
            quantity = parse_decimal(qty_text)
            if quantity is None:
                confidence = 0.5
                warnings.append(f"page {page_no} row {row_counter}: quantity '{qty_text}' is not numeric")
            if not description:
                confidence = min(confidence, 0.4)
                warnings.append(f"page {page_no} row {row_counter}: empty description for {item_number}")
            eff_from, eff_thru = _text(cols, "effective_from"), _text(cols, "effective_thru")
            d_from, d_thru = _parse_date(eff_from), _parse_date(eff_thru)
            is_active = True
            if as_of and d_thru and d_thru < as_of:
                is_active = False
            if as_of and d_from and d_from > as_of:
                is_active = False
            category, reason = categorize(item_number, description, quantity)
            bbox = line_bbox(line)
            redlines = [
                {"field": _field_for_x(bands, a.cx), "text": a.content}
                for a in annots
                if a.content and a.y1 >= bbox.y0 - 4 and a.y0 <= bbox.y1 + 10
            ]
            items.append(
                DocumentItem(
                    id=f"{doc_id}:r{row_counter}",
                    doc_id=doc_id,
                    doc_type=DocType.BOM,
                    sku=header.get("parent_item"),
                    item_number=item_number,
                    description=description,
                    quantity=quantity,
                    uom=_text(cols, "um") or None,
                    oper_seq=_text(cols, "oper_seq") or None,
                    attributes={
                        "level": level,
                        "branch_plant": _text(cols, "branch_plant"),
                        "ext_qty": _text(cols, "ext_qty"),
                        "t": _text(cols, "t"),
                        "effective_from": eff_from,
                        "effective_thru": eff_thru,
                        "flags": _text(cols, "flags"),
                        "redlines": redlines,
                    },
                    category=category,
                    category_reason=reason,
                    is_active=is_active,
                    extraction_confidence=confidence,
                    evidence=Evidence(
                        file=str(path),
                        file_sha256=sha,
                        page=page_no,
                        bbox=bbox,
                        raw_text=line_text(line),
                        line_index=row_counter - 1,
                        locator=f"page {page_no}, row {row_counter}",
                    ),
                )
            )
    pdf.close()
    if not header.get("parent_item"):
        warnings.append("parent item not found in header")
    return Document(
        id=doc_id,
        doc_type=DocType.BOM,
        path=str(path),
        sha256=sha,
        sku=header.get("parent_item"),
        header=header,
        items=items,
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        warnings=warnings,
    )


def _parse_header(lines: list[list[Word]], header: dict[str, str]) -> None:
    for line in lines:
        text = line_text(line)
        for key, rx in _HEADER_PATTERNS.items():
            if key in header:
                continue
            m = rx.search(text)
            if m:
                header[key] = m.group(1).strip()


def _field_for_x(bands: list[ColumnBand], x: float) -> str:
    return min(bands, key=lambda b: b.distance(x)).name

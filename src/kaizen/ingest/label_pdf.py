"""Parser for product labels: REF, product name, and the 'Full Kit - Contents' list.

Layout-aware: kit-content entries are detected by their 'N Each -' starters; the x positions of those starters
define the columns; continuation (wrapped) lines are merged into the entry above them within the same column.
"""

import re
import statistics
from collections import Counter
from pathlib import Path

import pymupdf

from kaizen.ingest.hashing import document_id, sha256_file
from kaizen.ingest.ocr import ocr_available, ocr_min_confidence, ocr_page, ocr_words
from kaizen.ingest.pdf_words import Word, extract_words, group_lines, line_bbox, line_text
from kaizen.ingest.quantity import parse_label_line
from kaizen.models import BBox, DocType, Document, DocumentItem, Evidence, ItemCategory

PARSER_NAME = "label_pdf"
PARSER_VERSION = "1"

_REF_CODE_RE = re.compile(r"^[A-Z0-9]{5,12}$")
_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")
_UOM_WORDS = {"EACH", "EA", "PAIR", "PAIRS", "PACK", "PACKS", "PKG", "PCS", "PC", "ROLL", "ROLLS", "SET", "SETS"}
_TERMINATOR_PREFIXES = ("store between", "lot ", "assembled", "(01)", "ref ")
_TERMINATOR_CONTAINS = ("are trademarks", "registered trademark")
_COLUMN_GAP = 40.0
_COLUMN_TOLERANCE = 6.0


def _is_starter(words: list[Word], i: int) -> bool:
    return bool(_NUMBER_RE.match(words[i].text)) and i + 1 < len(words) and words[i + 1].text.upper() in _UOM_WORDS


def _find_ref(lines: list[list[Word]]) -> tuple[str | None, int, int | None]:
    counts: Counter[str] = Counter()
    first_line: dict[str, int] = {}
    for idx, line in enumerate(lines):
        for i, w in enumerate(line[:-1]):
            if w.text.upper().rstrip(":") == "REF" and _REF_CODE_RE.match(line[i + 1].text):
                code = line[i + 1].text
                counts[code] += 1
                first_line.setdefault(code, idx)
    if not counts:
        return None, 0, None
    best = max(counts, key=lambda c: (counts[c], -first_line[c]))
    return best, counts[best], first_line[best]


def _is_terminator(text: str) -> bool:
    low = text.lower()
    return low.startswith(_TERMINATOR_PREFIXES) or any(s in low for s in _TERMINATOR_CONTAINS)


def _cluster_columns(x0s: list[float]) -> list[float]:
    cols: list[float] = []
    for x in sorted(x0s):
        if not cols or x - cols[-1] > _COLUMN_GAP:
            cols.append(x)
    return cols


def _column_of(x: float, columns: list[float]) -> int:
    idx = 0
    for i, cx in enumerate(columns):
        if x >= cx - _COLUMN_TOLERANCE:
            idx = i
    return idx


def parse_label_pdf(path: Path | str) -> Document:
    path = Path(path)
    sha = sha256_file(path)
    doc_id = document_id("label", sha, path)
    pdf = pymupdf.open(path)
    header: dict = {}
    items: list[DocumentItem] = []
    warnings: list[str] = []
    method = "none"
    for page in pdf:
        page_no = page.number + 1
        words = extract_words(page)
        page_method, confidence_cap = "pdf_text", 1.0
        if not words:
            if page.get_images(full=True) and ocr_available():
                result = ocr_page(page)
                words = ocr_words(result)
                page_method, confidence_cap = "ocr", ocr_min_confidence(result)
                header["ocr_engine"] = result.engine
                warnings.append(f"page {page_no}: no native text; OCR ({result.engine}, {result.dpi} dpi) produced {len(words)} words, min confidence {confidence_cap:.2f} — verify against the page image")
            elif page.get_images(full=True):
                warnings.append(f"page {page_no}: image-only page and no OCR engine installed (pip install rapidocr-onnxruntime); nothing extracted — OCR NOT IMPLEMENTED in this environment")
            else:
                warnings.append(f"page {page_no}: no text found")
        if words:
            method = page_method if method == "none" else method
        lines = group_lines(words, y_tol=2.5)
        if not lines:
            continue
        ref, ref_count, ref_line = _find_ref(lines)
        if ref and "ref" not in header:
            header["ref"] = ref
            header["ref_occurrences"] = ref_count
        anchor = next((i for i, l in enumerate(lines) if "contents" in line_text(l).lower()), None)
        if anchor is None:
            warnings.append(f"page {page_no}: no 'Contents' heading found; no kit-content lines extracted")
            continue
        if "product_name" not in header:
            start = (ref_line + 1) if ref_line is not None else 0
            header["product_name"] = " ".join(line_text(l) for l in lines[start:anchor]).strip()
        region = _contents_region(lines[anchor + 1 :])
        starters = [w.x0 for line in region for i, w in enumerate(line) if _is_starter(line, i)]
        columns = _cluster_columns(starters) if starters else [min(w.x0 for l in region for w in l)] if region else [0.0]
        entries = _build_entries(region, columns)
        for col_idx, col_entries in enumerate(entries):
            for k, entry_words in enumerate(col_entries, start=1):
                text = " ".join(w.text for w in entry_words)
                parsed = parse_label_line(text)
                if not parsed.matched:
                    warnings.append(f"page {page_no}: unparsed text in contents region skipped: '{text[:60]}'")
                    continue
                line_count = len({round(w.cy) for w in entry_words})
                confidence = confidence_cap
                if len(parsed.description) < 3 or parsed.description.endswith(","):
                    confidence = 0.7
                    warnings.append(f"page {page_no}: suspicious description '{parsed.description}'")
                bbox = _union([line_bbox([w]) for w in entry_words])
                items.append(
                    DocumentItem(
                        id=f"{doc_id}:c{col_idx + 1}e{k}",
                        doc_id=doc_id,
                        doc_type=DocType.LABEL,
                        sku=header.get("ref"),
                        item_number=None,
                        description=parsed.description,
                        quantity=parsed.quantity,
                        uom=parsed.uom,
                        sub_quantity=parsed.sub_quantity,
                        attributes={"column": col_idx + 1, "line_count": line_count, "raw_line": text},
                        category=ItemCategory.PHYSICAL_COMPONENT,
                        category_reason="kit-contents line on the product label",
                        extraction_confidence=confidence,
                        evidence=Evidence(
                            file=str(path),
                            file_sha256=sha,
                            page=page_no,
                            bbox=bbox,
                            raw_text=text,
                            line_index=len(items),
                            locator=f"page {page_no}, contents column {col_idx + 1}, entry {k}",
                            extraction_method=page_method,
                        ),
                    )
                )
    pdf.close()
    header["extraction_method"] = method
    if "ref" not in header:
        warnings.append("REF number not found")
    return Document(
        id=doc_id,
        doc_type=DocType.LABEL,
        path=str(path),
        sha256=sha,
        sku=header.get("ref"),
        header=header,
        items=items,
        parser_name=PARSER_NAME,
        parser_version=PARSER_VERSION,
        warnings=warnings,
    )


def _contents_region(lines: list[list[Word]]) -> list[list[Word]]:
    heights = [max(w.y1 for w in l) - min(w.y0 for w in l) for l in lines] or [8.0]
    h = statistics.median(heights)
    region: list[list[Word]] = []
    prev_y1: float | None = None
    for line in lines:
        text = line_text(line)
        y0 = min(w.y0 for w in line)
        if _is_terminator(text):
            break
        if region and prev_y1 is not None and y0 - prev_y1 > 2.5 * h:
            break
        region.append(line)
        prev_y1 = max(w.y1 for w in line)
    return region


def _build_entries(region: list[list[Word]], columns: list[float]) -> list[list[list[Word]]]:
    entries: list[list[list[Word]]] = [[] for _ in columns]
    for line in region:
        per_col: dict[int, list[Word]] = {}
        for w in line:
            per_col.setdefault(_column_of(w.x0, columns), []).append(w)
        for col_idx, words in per_col.items():
            words.sort(key=lambda w: w.x0)
            if _is_starter(words, 0) or not entries[col_idx]:
                entries[col_idx].append(list(words))
            else:
                entries[col_idx][-1].extend(words)
    return entries


def _union(boxes: list[BBox]) -> BBox:
    out = boxes[0]
    for b in boxes[1:]:
        out = out.union(b)
    return out

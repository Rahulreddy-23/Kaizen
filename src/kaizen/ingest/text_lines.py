"""Keep recognized page text separately from the lines selected for comparisons."""

import statistics
from bisect import bisect_right
from difflib import SequenceMatcher

from kaizen.ingest.pdf_words import Word, group_lines, line_bbox, line_text, split_line_by_gaps
from kaizen.models import DocType, DocumentItem, Evidence, ItemCategory


def capture_text_lines(words: list[Word], *, doc_id: str, doc_type: DocType, file: str, sha: str, page: int, method: str,
                       column_cuts: tuple[float, ...] = (), column_y: tuple[float, float] | None = None,
                       reference_words: list[Word] | None = None) -> list[DocumentItem]:
    """Use known layout boundaries before grouping nearby words on a baseline.

    Column boundaries apply only to the supplied body band; spanning headers and
    footers remain intact. A native layer may supply whitespace, never characters.
    Original OCR text and boxes remain available as evidence.
    """
    def fragments(source):
        lines = group_lines(source, y_tol=2.5)
        height = statistics.median(max(w.y1 for w in line) - min(w.y0 for w in line) for line in lines) if lines else 7
        result = []
        for line in lines:
            columns: dict[int, list[Word]] = {}
            for word in line:
                col = bisect_right(column_cuts, word.x0) if column_y and column_y[0] <= word.cy <= column_y[1] else -1
                columns.setdefault(col, []).append(word)
            result.extend(fragment for column in columns.values() for fragment in split_line_by_gaps(column, 2.5 * height))
        return result

    references = [(line_bbox(line), line_text(line)) for line in fragments(reference_words or [])]
    items = []
    for n, line in enumerate(fragments(words), start=1):
        raw = text = line_text(line)
        box = line_bbox(line)
        candidates = [(SequenceMatcher(None, ''.join(raw.lower().split()), ''.join(ref.lower().split()), autojunk=False).ratio(), ref)
                      for bounds, ref in references if box.x0 < bounds.x1 and bounds.x0 < box.x1 and box.y0 < bounds.y1 and bounds.y0 < box.y1]
        if candidates:
            text = restore_supported_spacing(raw, max(candidates)[1])
        items.append(DocumentItem(
            id=f"{doc_id}:text:p{page}l{n}", doc_id=doc_id, doc_type=doc_type,
            description=text, category=ItemCategory.DOCUMENT,
            category_reason="Recognized source text; not a component comparison",
            attributes={"kind": "source_text", "native_spacing_recovered": text != raw}, extraction_confidence=min(w.confidence for w in line),
            evidence=Evidence(file=file, file_sha256=sha, page=page, bbox=box, raw_text=raw, line_index=n,
                              locator=f"page {page}, source text line {n}", extraction_method=method),
        ))
    return items


def restore_supported_spacing(text: str, reference: str) -> str:
    """Transfer whitespace only across matching characters in a damaged text layer.

    OCR retains every character, identifier and number. The native layer supplies
    word boundaries only; disagreement cannot introduce replacement letters.
    """
    def compact(value):
        chars, boundaries = [], set()
        for char in value:
            if char.isspace():
                if chars:
                    boundaries.add(len(chars))
            else:
                chars.append(char)
        return ''.join(chars), boundaries

    source, boundaries = compact(text)
    native, native_spaces = compact(reference)
    matcher = SequenceMatcher(None, source.lower(), native.lower(), autojunk=False)
    if matcher.ratio() < .85:
        return text
    mapping = {b + k: a + k for a, b, size in matcher.get_matching_blocks() for k in range(size)}
    for boundary in native_spaces:
        left, right = mapping.get(boundary - 1), mapping.get(boundary)
        if left is not None and right == left + 1:
            boundaries.add(right)
    return ''.join((' ' if n in boundaries else '') + char for n, char in enumerate(source))

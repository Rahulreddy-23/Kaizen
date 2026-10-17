"""Keep recognized page text separately from the lines selected for comparisons."""

import statistics

from kaizen.ingest.pdf_words import Word, group_lines, line_bbox, line_text, split_line_by_gaps
from kaizen.models import DocType, DocumentItem, Evidence, ItemCategory


def capture_text_lines(words: list[Word], *, doc_id: str, doc_type: DocType, file: str, sha: str, page: int, method: str) -> list[DocumentItem]:
    lines = group_lines(words, y_tol=2.5)
    height = statistics.median(max(w.y1 for w in line) - min(w.y0 for w in line) for line in lines) if lines else 7
    fragments = [fragment for line in lines for fragment in split_line_by_gaps(line, 2.5 * height)]
    return [
        DocumentItem(
            id=f"{doc_id}:text:p{page}l{n}", doc_id=doc_id, doc_type=doc_type,
            description=line_text(line), category=ItemCategory.DOCUMENT,
            category_reason="Recognized source text; not a component comparison",
            attributes={"kind": "source_text"}, extraction_confidence=min(w.confidence for w in line),
            evidence=Evidence(file=file, file_sha256=sha, page=page, bbox=line_bbox(line), raw_text=line_text(line), line_index=n,
                              locator=f"page {page}, source text line {n}", extraction_method=method),
        ) for n, line in enumerate(fragments, start=1)
    ]


def restore_supported_spacing(text: str, reference: str) -> str:
    """Transfer whitespace only across matching characters in a damaged text layer.

    OCR retains every character, identifier and number. The native layer supplies
    word boundaries only; disagreement cannot introduce replacement letters.
    """
    from difflib import SequenceMatcher

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

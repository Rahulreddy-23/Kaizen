"""Marked-up BOM, label and drawing PDFs: the digital version of the coloured check marks reviewers
draw on printouts.

A mark wears the colour of the document it was compared *against*, so one key reads correctly whichever
document you are holding: the BOM↔drawing check is purple on the BOM, because it was checked against
the drawing, and blue on the drawing, because it was checked against the BOM. Only the BOM carries a
legend, which is what the real BD sheets do.

Shape = the decision: tick = agrees, cross = discrepancy. There is no third shape. A row nobody has
settled gets no mark at all, because these documents leave the building and ink that does not mean
'a reviewer decided this' reads like ink that does.

Placement differs by document, because the documents differ:
  * BOM — a table, so each mark goes in the column that check verified. Columns are measured from the
    ink on the page, never assumed, because the JDE form prints at different widths. A BOM whose
    columns cannot be read falls back to the right margin.
  * label and drawing — a layout, not a table, so there is no shared gutter to find. The evidence box
    already points at the exact field, so marks sit just right of it, stacking into one column on a row
    too narrow to take them side by side.

A BOM with no page geometry (XLSX/CSV source) gets a separate review page instead of guessed positions."""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pymupdf

from kaizen.ingest.pdf_words import extract_words
from kaizen.models import DocType, Document, Run, Severity

# Every document has a colour, and a mark wears the colour of the document it was compared against.
# So green means 'the label agrees' on the BOM and on the drawing alike, and a reviewer learns the four
# colours once. This is what the real BD sheets do: their drawings carry blue marks for the label check.
DOC_COLORS = {"BOM": (0.05, 0.35, 0.9), "LABEL": (0.05, 0.55, 0.15), "DRAWING": (0.55, 0.1, 0.75), "PCO": (0.95, 0.5, 0.05)}
DOC_NAMES = {"BOM": "BOM", "LABEL": "Label", "DRAWING": "PKG Drawings", "PCO": "PCO"}
# The two documents each check compares. LABEL_REVISION is absent on purpose: it compares a label with
# its own earlier revision, so there is no other document to name and it earns no mark.
CHECK_PARTIES = {"BOM_LABEL": ("BOM", "LABEL"), "BOM_DRAWING": ("BOM", "DRAWING"), "LABEL_DRAWING": ("LABEL", "DRAWING"), "PCO_BOM": ("PCO", "BOM")}
MARK_ORDER = ("BOM", "LABEL", "DRAWING", "PCO")  # left-to-right order of marks sharing one row
# Legend lines, written on the BOM only — the real label and drawing carry marks and no legend.
CHECK_LABELS = {"BOM_LABEL": "Compared with Label", "BOM_DRAWING": "Compared with PKG Drawings", "PCO_BOM": "Compared with PCO"}
CHECK_OFFSETS = {check: 9.0 * i for i, check in enumerate(CHECK_PARTIES)}
MARK = 6.0
COLUMN_MARK = 9.0  # on-row marks sit in measured gutters, so they can be drawn at reading size
GAP = 2.0  # between two marks that share a row
PAD = 3.0  # between the verified text and its first mark
COLUMN_SPLIT = 72.0  # an inch: fields starting further apart than this are in different text columns
_QUANTITY = re.compile(r"^\d+\.\d{4}$")  # 'Quantity Per'; 'Ext Qty' carries six decimals
_FONT = pymupdf.Font("helv")


@dataclass(frozen=True)
class Mark:
    page: int
    item: str
    check: str
    kind: str  # clear | discrepancy | review
    x: float
    y: float


@dataclass
class AnnotatedOutcome:
    path: Path
    marks: int
    fallback: bool
    mark_list: list[Mark] = field(default_factory=list)


def _kind(r, review_states: dict[str, str] | None) -> str | None:
    """The mark a row has earned, or None when it has earned none.

    Two things can settle a row, and a reviewer always outranks the tool. A decision on file is used
    as given. Without one the comparison answers for itself: a confident agreement earns a tick and a
    real discrepancy earns a cross, because a check the tool ran is still a check somebody can read.

    What the tool will not do is guess. A row it could not settle — `requires_validation` — gets no
    mark at all and waits for a person, which is the one case where ink would claim more than anybody
    knows. These documents leave the building, so an unsure row is better blank than optimistic.
    """
    if review_states:
        st = review_states.get(r.row_id)
        if st == "clear":
            return "clear"
        if st == "discrepancy":
            return "discrepancy"
    if any(d.severity is not Severity.INFO for d in r.discrepancies) or r.classification.value in ("MISMATCH", "MISSING"):
        return "discrepancy"
    if r.requires_validation:
        return None
    return "clear"


def _other(check: str, doc_type: str) -> str | None:
    """The document `check` compared this one against, or None when the check does not touch it.

    This single function is the whole colour rule, and the reason the same green means 'the label
    agrees' whether you are holding the BOM or the drawing.
    """
    parties = CHECK_PARTIES.get(check)
    if parties is None or doc_type not in parties:
        return None
    return parties[1] if parties[0] == doc_type else parties[0]


def _checks_for(doc_type: str) -> list[str]:
    """Checks that can mark this document, in the order their marks sit on a row."""
    found = [(MARK_ORDER.index(other), check) for check in CHECK_PARTIES if (other := _other(check, doc_type))]
    return [check for _, check in sorted(found)]


def _rows(run: Run, doc: Document):
    """Every check row that points at this document, with the item it points at.

    LABEL_REVISION never appears, because it is absent from CHECK_PARTIES: it compares a label with its
    own earlier revision, and only the latest label is marked. Superseded labels get nothing at all.
    """
    if doc.header.get("revision_role") == "old":
        return
    allowed = set(_checks_for(doc.doc_type.value))
    for r in run.results:
        if r.role != "item" or r.check.value not in allowed:
            continue
        if r.source_a is not None and r.source_a.doc_id == doc.id:
            yield r, r.source_a
        elif r.source_b is not None and r.source_b.doc_id == doc.id:
            yield r, r.source_b


def _data_rows(page: pymupdf.Page):
    """Rows of the component table. Each one starts at the far left with a level number."""
    bands: dict[int, list] = defaultdict(list)
    for w in extract_words(page):
        bands[round((w.y0 + w.y1) / 2)].append(w)
    for y, band in sorted(bands.items()):
        band.sort(key=lambda w: w.x0)
        if band and band[0].x0 <= 45 and band[0].text.isdigit():
            yield y, band


def _column_anchors(page: pymupdf.Page) -> dict[str, float] | None:
    """One x per check, each centred in a gutter that carries no ink on any component row.

    The JDE form prints at different column widths, and its values do not line up with its own
    headings — quantities are right-aligned past 'Per'. So the columns are measured from the ink
    instead. Returns None when the page is not a component table or its columns cannot be told
    apart; the caller then falls back to the right margin.
    """
    rows = list(_data_rows(page))
    if len(rows) < 2:
        return None
    spans = sorted((w.x0, w.x1) for _, band in rows for w in band)
    free, edge = [], spans[0][1]
    for x0, x1 in spans:
        if x0 - edge >= COLUMN_MARK + 4:
            free.append((edge, x0))
        edge = max(edge, x1)
    quantity = [(w.x0, w.x1) for _, band in rows for w in band if _QUANTITY.match(w.text)]
    if not quantity:
        return None
    left, right = min(x0 for x0, _ in quantity), max(x1 for _, x1 in quantity)
    before = [g for g in free if g[1] <= left + 1]
    after = [g for g in free if g[0] >= right - 1]
    # before[0] is the gutter between the level number and the component item, so the
    # component item's own gutter is before[1]; the label mark goes beside the quantity.
    if len(before) < 3 or not after:
        return None
    return {"BOM_DRAWING": _centre(before[1]), "BOM_LABEL": _centre(before[-1]), "PCO_BOM": _centre(after[0])}


def _centre(gutter: tuple[float, float]) -> float:
    return (gutter[0] + gutter[1]) / 2 - COLUMN_MARK / 2


def _draw_mark(page: pymupdf.Page, kind: str, x: float, y: float, color, size: float = MARK, width: float = 1.1) -> None:
    shape = page.new_shape()
    s = size
    def point(px, py):
        return pymupdf.Point(px, py) * page.derotation_matrix
    if kind == "clear":
        # A drawn check: a short stroke down into the corner, then a long one up past it.
        # Kept symmetric about y so the mark still centres on the row it belongs to.
        shape.draw_line(point(x, y + s * 0.02), point(x + s * 0.33, y + s * 0.48))
        shape.draw_line(point(x + s * 0.33, y + s * 0.48), point(x + s, y - s * 0.48))
    else:
        # A cross. Only a settled row ever reaches here, so these two marks are the whole vocabulary.
        shape.draw_line(point(x, y - s * 0.5), point(x + s, y + s * 0.5))
        shape.draw_line(point(x, y + s * 0.5), point(x + s, y - s * 0.5))
    # closePath defaults to True, which joins the last point back to the first: a tick becomes a
    # filled-looking triangle and a cross becomes a bowtie. Two open strokes are the whole mark.
    shape.finish(color=color, width=width, closePath=False, lineJoin=1, lineCap=1)
    shape.commit()


def _updated_on(run: Run, updated: str | None) -> str:
    """The day this document last changed, as dd-mm-yyyy.

    A document changes when a reviewer decides a row, so the newest decision is its update date. A run
    nobody has reviewed yet has only ever been compared, and its own date is the honest answer there.
    """
    stamp = run.metadata.timestamp
    if updated:
        try:
            stamp = datetime.fromisoformat(updated)
        except ValueError:
            pass  # a stored date we cannot read must not fail a download; the run date still tells the truth
    return stamp.strftime("%d-%m-%Y")


def _top_date(page: pymupdf.Page, text: str) -> bool:
    """Write `text` in the clear band across the top of the page. False when there is no room.

    The label and the drawing carry no legend, so this one line is everything they say about
    themselves. A real PKG drawing can be a scan with no text on it at all, so the search tests the
    line's own rectangle against every kind of ink — words, vector strokes and placed images — rather
    than against words alone, and gives up rather than print over the drawing.
    """
    size = 8.0
    width = _FONT.text_length(text, size)
    ink = [pymupdf.Rect(w.x0, w.y0, w.x1, w.y1) for w in extract_words(page)]
    # get_drawings and get_image_rects answer in unrotated space, while words come back as displayed.
    ink += [d["rect"] * page.rotation_matrix for d in page.get_drawings()]
    ink += [r * page.rotation_matrix for im in page.get_images() for r in page.get_image_rects(im[0])]
    for y in (6.0 + 2.0 * step for step in range(16)):  # the top 38pt, in 2pt steps, clear of the trim edge
        for x in (8.0, page.rect.width - width - 8.0):
            box = pymupdf.Rect(x, y, x + width, y + size + 2)
            if box.x0 < 0 or box.y1 > page.rect.height or any(box.intersects(i) for i in ink):
                continue
            # The search works in displayed coordinates, because 'the top of the page' is what a reader
            # sees. A rotated page stores its ink unrotated, so the baseline converts back before
            # writing, and the glyphs carry the page's own rotation - without both, the date lands in
            # a corner nobody asked for, or reads sideways. A real PKG drawing arrives rotated 270.
            baseline = pymupdf.Point(box.x0, box.y1 - 3) * page.derotation_matrix
            page.insert_text(baseline, text, fontname="helv", fontsize=size, color=(0.8, 0.1, 0.1), rotate=page.rotation)
            return True
    return False


def write_annotated(run: Run, document: Document, out_path: Path | str, checked_by: list[str] | None = None, review_states: dict[str, str] | None = None, updated: str | None = None) -> AnnotatedOutcome:
    """Copy `document` and draw the coloured check marks it has earned onto it.

    Only the BOM gets a legend and a 'Checked by' stamp: the colours mean the same thing on all three
    documents, so the BOM's key explains the label and the drawing as well. That is also what the real
    sheets do — their labels and drawings carry marks and no legend. All three do carry the date they
    were last updated, because a marked document is worthless without knowing how current it is.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(_rows(run, document))
    has_geometry = document.path.lower().endswith(".pdf") and any(item.evidence.bbox is not None and item.evidence.page for _, item in rows)
    if not has_geometry:
        return _fallback_page(run, document, rows, out_path, checked_by, review_states, updated)
    doc = pymupdf.open(document.path)
    marks = mark_document(doc, run, document, checked_by, review_states, updated)
    doc.save(out_path)
    doc.close()
    return AnnotatedOutcome(out_path, len(marks), False, marks)


def mark_document(doc: pymupdf.Document, run: Run, document: Document, checked_by: list[str] | None = None, review_states: dict[str, str] | None = None, updated: str | None = None) -> list[Mark]:
    """Draw this document's marks onto an already-open copy of it, and return what was drawn.

    Separate from `write_annotated` because the marks are wanted in two places: saved into a PDF the
    reviewer downloads, and drawn before a single page is rasterised for the side-by-side reader. Both
    go through here, so the picture on screen and the file on disk cannot drift apart.
    """
    rows = list(_rows(run, document))
    if document.doc_type is DocType.BOM:
        marks = _mark_table(doc, rows, review_states)
        _stamp(doc[0], run, document, checked_by, updated)
        return marks
    _top_date(doc[0], f"Updated {_updated_on(run, updated)}")
    return _mark_beside(doc, document.doc_type.value, rows, review_states)


def _mark_table(doc: pymupdf.Document, rows, review_states) -> list[Mark]:
    """BOM marks: one per measured column, so each mark sits beside the value that check verified."""
    marks: list[Mark] = []
    margin_x: dict[int, float] = {}
    anchors: dict[int, dict[str, float] | None] = {}
    for r, item in rows:
        ev = item.evidence
        if ev.bbox is None or not ev.page or ev.page > len(doc):
            continue
        kind = _kind(r, review_states)
        if kind is None:
            continue
        page = doc[ev.page - 1]
        if ev.page not in anchors:
            anchors[ev.page] = _column_anchors(page)
        column = anchors[ev.page]
        y = (ev.bbox.y0 + ev.bbox.y1) / 2
        x = column.get(r.check.value) if column else None
        if x is None:  # columns unreadable, or a check this form has no column for: use the margin
            if ev.page not in margin_x:
                words = extract_words(page)
                max_x1 = max((w.x1 for w in words), default=page.rect.width - 40)
                base = max_x1 + 4
                if base + 3 * 9 + MARK > page.rect.width - 2:
                    base = page.rect.width - 2 - 3 * 9 - MARK  # squeeze into whatever margin remains
                margin_x[ev.page] = max(base, max_x1 + 1)
            x, size, width = margin_x[ev.page] + CHECK_OFFSETS[r.check.value], MARK, 1.1
        else:
            size, width = COLUMN_MARK, 1.6
        _draw_mark(page, kind, x, y, DOC_COLORS[_other(r.check.value, "BOM")], size, width)
        marks.append(Mark(ev.page, item.item_number or "", r.check.value, kind, x, y))
    return marks


def _mark_beside(doc: pymupdf.Document, doc_type: str, rows, review_states) -> list[Mark]:
    """Label and drawing marks: in a tidy column after the text block the checks looked at.

    These documents are layouts, not tables, so there is no printed gutter to measure. Instead the
    marked fields are grouped into the page's own text columns, and each column gets one x that clears
    every row in it — so the marks line up the way a reviewer's pen would, rather than following the
    ragged right edge of the wording. A column that admits no such x falls back to per-row placement.
    """
    fields: dict[tuple, dict] = {}
    for r, item in rows:
        ev = item.evidence
        if ev.bbox is None or not ev.page or ev.page > len(doc):
            continue
        kind = _kind(r, review_states)
        if kind is None:
            continue  # the field is never created, so an unsettled row cannot shrink the other marks
        key = (ev.page, round(ev.bbox.x1, 1), round((ev.bbox.y0 + ev.bbox.y1) / 2, 1))
        field = fields.setdefault(key, {"page": ev.page, "bbox": ev.bbox, "item": item.item_number or "", "kinds": {}})
        field["kinds"][r.check.value] = kind
    for field in fields.values():
        field["checks"] = [c for c in _checks_for(doc_type) if c in field["kinds"]]

    pages: dict[int, list[dict]] = defaultdict(list)
    for field in fields.values():
        pages[field["page"]].append(field)

    words_by_page = {page_no: [pymupdf.Rect(w.x0, w.y0, w.x1, w.y1) for w in extract_words(doc[page_no - 1])] for page_no in pages}
    columns = {page_no: _text_columns(on_page) for page_no, on_page in pages.items()}
    size, plan = _fit(doc, pages, columns, words_by_page)

    marks: list[Mark] = []
    for page_no in pages:
        page = doc[page_no - 1]
        words = words_by_page[page_no]
        # Per-field placement must clear the marks already drawn as well as the words, or two items on
        # one line put their marks on top of each other. A shared column needs no such care: _fit has
        # already proved every mark on the page clears every other.
        taken = list(words)
        for index, column in enumerate(columns[page_no]):
            shared = plan.get((page_no, index))
            for field in column:
                y = (field["bbox"].y0 + field["bbox"].y1) / 2
                count = len(field["checks"])
                places = _spots(shared[0], y, count, shared[1], size) if shared else _clear_places(page, taken, field["bbox"], count, size)
                if not shared:
                    taken.extend(pymupdf.Rect(px, py - size / 2, px + size, py + size / 2) for px, py in places)
                for check, (x, my) in zip(field["checks"], places):
                    _draw_mark(page, field["kinds"][check], x, my, DOC_COLORS[_other(check, doc_type)], size, 1.6)
                    marks.append(Mark(page_no, field["item"], check, field["kinds"][check], x, my))
    return marks


def _fit(doc, pages: dict[int, list[dict]], columns: dict[int, list[list[dict]]], words_by_page) -> tuple[float, dict]:
    """The largest mark size that lets every text column line up, and where each column's marks go.

    One size for the whole document, because marks that change size page to page read as a mistake.
    Sizes are tried from the largest downwards until every column has a shared x that clears the words
    and every mark on the page, its own column's and its neighbours': a label's crowded left column has
    18.9pt of gutter and lines 8.5pt apart, so its marks come out small, while a drawing's roomy
    callouts keep the full 9pt. A size that cannot satisfy every column is simply not used, which is
    what keeps a crowded column from solving its problem by drifting into the next column's space.
    """
    # A page with two text columns gets no shared x at all. One column's widest row would push its
    # marks past the other column's words, which is how a left-column item ended up with its marks
    # 140pt away, beyond the right column — close enough to that column's own marks to read as four
    # marks on one item. Those pages place each field beside its own text instead.
    shared_pages = [page_no for page_no in pages if len(columns[page_no]) == 1]
    wanted = sum(len(columns[page_no]) for page_no in shared_pages)
    if not wanted:
        return COLUMN_MARK, {}
    size = COLUMN_MARK
    while size >= 4.0:
        plan, boxes = {}, defaultdict(list)
        for page_no in shared_pages:
            for index, column in enumerate(columns[page_no]):
                shared = _shared_column(doc[page_no - 1], words_by_page[page_no], column, size)
                if shared is None:
                    continue
                plan[(page_no, index)] = shared
                boxes[page_no].extend(_boxes(column, *shared, size))
        page_clear = all(not a.intersects(b) for drawn in boxes.values()
                         for i, a in enumerate(drawn) for b in drawn[i + 1:])
        if page_clear and len(plan) == wanted:
            return size, plan
        size -= 0.5
    return COLUMN_MARK, {}


def _boxes(column: list[dict], x: float, stacked: bool, size: float) -> list[pymupdf.Rect]:
    """The rectangles this column's marks would occupy at this x and layout."""
    return [pymupdf.Rect(px, py - size / 2, px + size, py + size / 2)
            for field in column
            for px, py in _spots(x, (field["bbox"].y0 + field["bbox"].y1) / 2, len(field["checks"]), stacked, size)]


def _text_columns(fields: list[dict]) -> list[list[dict]]:
    """The page's marked fields, split into its text columns by where each field starts."""
    columns: list[list[dict]] = []
    for marked in sorted(fields, key=lambda f: f["bbox"].x0):
        if columns and marked["bbox"].x0 - columns[-1][-1]["bbox"].x0 <= COLUMN_SPLIT:
            columns[-1].append(marked)
        else:
            columns.append([marked])
    return columns


def _spots(x: float, y: float, count: int, stacked: bool, size: float) -> list[tuple[float, float]]:
    """Where `count` marks go, either in a row rightwards from x or in a column centred on y."""
    if not stacked:
        return [(x + i * (size + GAP), y) for i in range(count)]
    height = count * size + (count - 1) * GAP
    return [(x, y - height / 2 + size / 2 + i * (size + GAP)) for i in range(count)]


def _is_clear(words: list[pymupdf.Rect], places: list[tuple[float, float]], size: float) -> bool:
    """True when no mark at these positions would touch a printed word.

    Tested as real rectangles: a mark is 9pt tall, so a word on the line above can foul it without ever
    crossing this row's centre line. That mistake put 36 marks over the label's own wording.
    """
    boxes = [pymupdf.Rect(x, y - size / 2, x + size, y + size / 2) for x, y in places]
    return all(not any(box.intersects(word) for word in words) for box in boxes)


def _shared_column(page: pymupdf.Page, words: list[pymupdf.Rect], column: list[dict], size: float) -> tuple[float, bool] | None:
    """One x and one layout that clears every field in this text column, or None if none does.

    Starting just past the longest line in the column, both layouts slide right until one works. A
    layout works only when its marks clear the printed words *and* each other: on a label the lines are
    8.5pt apart, so a stacked pair is taller than the row it belongs to and spills over its neighbours.
    Checking words alone let that through and put 63 of 68 marks on top of another mark.

    Nothing caps how far the marks may slide, because nothing needs to. A column that would have to
    travel far has already failed the test above at this size, so `_fit` lowers the size instead.
    """
    base = max(field["bbox"].x1 for field in column) + PAD
    widest = max(len(field["checks"]) for field in column)
    best: tuple[float, bool] | None = None
    for stacked in (False, True):
        span = size if stacked else widest * size + (widest - 1) * GAP
        x = base
        while x + span <= page.rect.width - 2:
            boxes = _boxes(column, x, stacked, size)
            crowded = any(a.intersects(b) for i, a in enumerate(boxes) for b in boxes[i + 1:])
            if not crowded and all(not any(box.intersects(word) for word in words) for box in boxes):
                if best is None or x < best[0]:
                    best = (x, stacked)
                break
            x += size / 2
    return best


def _clear_places(page: pymupdf.Page, words: list[pymupdf.Rect], bbox, count: int, size: float) -> list[tuple[float, float]]:
    """Fallback for one field whose column has no shared x: the first clear spot right of the text.

    Side by side is preferred, a column is tried next, and the pair slides right until it is clear,
    settling in the margin if it never is — a mark in the wrong place is recoverable, a mark over a
    part number is not.
    """
    y = (bbox.y0 + bbox.y1) / 2
    span = count * size + (count - 1) * GAP
    x = bbox.x1 + PAD
    while x + span <= page.rect.width - 2:
        for stacked in (False, True):
            places = _spots(x, y, count, stacked, size)
            if _is_clear(words, places, size):
                return places
        x += size / 2
    return _spots(max(page.rect.width - 2 - span, 0.0), y, count, False, size)


def _free_columns(page: pymupdf.Page, top: float, bottom: float, minimum: float) -> list[tuple[float, float]]:
    """x ranges carrying no ink between `top` and `bottom`, left to right."""
    spans = sorted((w.x0, w.x1) for w in extract_words(page) if top <= (w.y0 + w.y1) / 2 <= bottom)
    free, edge = [], 0.0
    for x0, x1 in spans:
        if x0 - edge >= minimum:
            free.append((edge + 10, x0 - 6))
        edge = max(edge, x1)
    if page.rect.width - edge >= minimum:
        free.append((edge + 10, page.rect.width - 6))
    return free


def _stamp(page: pymupdf.Page, run: Run, bom: Document, checked_by: list[str] | None, updated: str | None = None) -> None:
    """Legend and 'Checked by' block, placed in whatever the title band leaves empty.

    The legend is stacked, one check per line, each line in its own colour beside its own mark —
    the overlapping single row it replaces could not fit three labels across the page.

    Known limit: this block assumes an upright page. TextWriter with `matrix=derotation_matrix` lands
    correctly at rotation 0 and 180 but not at 90 or 270, where it drifts into a corner. Every BOM we
    have is upright, and `_top_date` shows the fix if a rotated one ever turns up: convert the point
    with `derotation_matrix` and write with `insert_text(..., rotate=page.rotation)`.
    """
    first_data = next((y for y, _ in _data_rows(page)), None)
    parent = next((w.y0 for w in extract_words(page) if w.text == "Parent"), None)
    bottom = (parent - 8) if parent else (first_data - 95 if first_data else 90)
    legend_width = max(_FONT.text_length(label, 9) for label in CHECK_LABELS.values()) + 20
    free = _free_columns(page, 18, bottom, 90)
    legend = next((g for g in reversed(free) if g[1] - g[0] >= legend_width), None)
    stamp = next((g for g in free if g is not legend), None)

    date = _updated_on(run, updated)
    if stamp is not None:
        w = pymupdf.TextWriter(page.rect)
        y = 28.0
        w.append((stamp[0], y), "Checked by", font=_FONT, fontsize=9)
        for n, name in enumerate(checked_by or [], 1):
            y += 12
            w.append((stamp[0], y), f"{n}) {name}", font=_FONT, fontsize=9)
        if not checked_by:
            # Nobody signed this run in the tool, so the block stays an empty line for a pen. Printing
            # 'names not recorded' puts an excuse on a document that leaves the building, where the
            # blank a reviewer fills in is both shorter and truer.
            y += 12
        w.append((stamp[0], y + 18), date, font=_FONT, fontsize=9)
        w.write_text(page, color=(0.8, 0.1, 0.1), matrix=page.derotation_matrix)

    if legend is None:
        return
    y = 28.0
    for check, label in CHECK_LABELS.items():
        writer = pymupdf.TextWriter(page.rect)
        writer.append((legend[0] + 18, y + 3), label, font=_FONT, fontsize=9)
        colour = DOC_COLORS[_other(check, "BOM")]
        writer.write_text(page, color=colour, matrix=page.derotation_matrix)
        _draw_mark(page, "clear", legend[0], y, colour, COLUMN_MARK, 1.6)
        y += 16
    key = pymupdf.TextWriter(page.rect)
    key.append((legend[0], y + 4), "tick = agrees    cross = discrepancy    no mark = needs a reviewer", font=_FONT, fontsize=6.5)
    key.write_text(page, color=(0.35, 0.35, 0.35), matrix=page.derotation_matrix)


def _fallback_page(run: Run, bom: Document, rows, out_path: Path, checked_by, review_states, updated: str | None = None) -> AnnotatedOutcome:
    kind = DOC_NAMES.get(bom.doc_type.value, bom.doc_type.value)
    columns = _checks_for(bom.doc_type.value)  # this document's own checks, not always the BOM's three
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    w = pymupdf.TextWriter(page.rect)
    names = ", ".join(checked_by) if checked_by else "____________________"  # a blank to sign, not an excuse
    w.append((30, 40), f"Annotated review page — {kind} {bom.sku} ({Path(bom.path).name})", font=_FONT, fontsize=11)
    w.append((30, 56), f"This {kind} has no page geometry to draw check marks on, so marks are listed per row instead.", font=_FONT, fontsize=7)
    w.append((30, 68), f"Checked by {names} | Kaizen Cross-Check {run.metadata.run_id} | Updated {_updated_on(run, updated)}", font=_FONT, fontsize=7)
    y = 92
    w.append((30, y), "Item", font=_FONT, fontsize=7)
    w.append((110, y), "Description", font=_FONT, fontsize=7)
    for i, check in enumerate(columns):
        w.append((330 + i * 90, y), DOC_NAMES[_other(check, bom.doc_type.value)], font=_FONT, fontsize=7)
    by_item: dict[str, dict] = {}
    for r, item in rows:
        entry = by_item.setdefault(item.item_number or item.id, {"desc": item.description, "marks": {}})
        entry["marks"][r.check.value] = _kind(r, review_states)
    marks: list[Mark] = []
    y += 12
    for item, entry in by_item.items():
        if y > 760:
            w.write_text(page)
            page = doc.new_page(width=612, height=792)
            w = pymupdf.TextWriter(page.rect)
            y = 40
        w.append((30, y), item, font=_FONT, fontsize=6.5)
        w.append((110, y), entry["desc"][:48], font=_FONT, fontsize=6.5)
        for i, check in enumerate(columns):
            kind = entry["marks"].get(check)
            if kind:
                x = 330 + i * 90
                _draw_mark(page, kind, x, y - 2, DOC_COLORS[_other(check, bom.doc_type.value)])
                marks.append(Mark(page.number + 1, item, check, kind, x, y))
        y += 11
    w.write_text(page)
    doc.save(out_path)
    doc.close()
    return AnnotatedOutcome(out_path, len(marks), True, marks)

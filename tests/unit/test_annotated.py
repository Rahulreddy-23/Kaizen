"""Marked-up BOM, label and drawing PDFs: a coloured mark per check, on the row and beside the value
that check verified, never over the original text; honest fallback when a BOM has no page geometry.

A mark wears the colour of the document it was compared against, so the same colour means the same
thing on all three documents. Only the BOM carries a legend, which is what the real BD sheets do."""

import re
from pathlib import Path

import pymupdf
import pytest

from kaizen.datasets.build import build_golden
from kaizen.ingest.pdf_words import extract_words
from kaizen.models import DocType, Thresholds
from kaizen.pipeline import run_folder
from kaizen.reporting.annotated import COLUMN_MARK, DOC_COLORS, GAP, MARK_ORDER, _kind, _other, _rows, _top_date, _updated_on, write_annotated
from kaizen.terminology.store import RelationshipStore


def added_marks(original: pymupdf.Document, marked: pymupdf.Document, page: int) -> list[dict]:
    """Drawings the annotator added to a page, told apart from the form the document already had."""
    was = {(round(d["rect"].x0, 2), round(d["rect"].y0, 2)) for d in original[page].get_drawings()}
    return [d for d in marked[page].get_drawings()
            if (round(d["rect"].x0, 2), round(d["rect"].y0, 2)) not in was and max(d["rect"].width, d["rect"].height) <= 14]


def doc_for(run, doc_type, sku, old=False):
    """Labels carry revision_role 'current' or 'old'; a BOM or drawing carries neither."""
    return next(d for d in run.documents if d.doc_type is doc_type and d.sku == sku
                and (d.header.get("revision_role") == "old") is old)


@pytest.fixture(scope="module")
def golden_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("g")
    golden = build_golden(root / "golden")
    return golden, run_folder(golden, RelationshipStore.default(), Thresholds())


def test_marks_sit_on_the_row_and_never_over_printed_text(golden_run, tmp_path):
    golden, run = golden_run
    bom = next(d for d in run.documents if d.doc_type is DocType.BOM and d.sku == "1295108FNS")
    before = [pymupdf.open(bom.path)[i].get_text() for i in range(len(pymupdf.open(bom.path)))]
    outcome = write_annotated(run, bom, tmp_path / "bom_annotated.pdf", checked_by=["Dharma A", "Hemant Gudihal"])
    assert outcome.fallback is False and outcome.marks >= 30
    doc = pymupdf.open(outcome.path)
    for i, text in enumerate(before):
        assert all(line in doc[i].get_text() for line in text.splitlines() if line.strip())
    page1 = doc[0].get_text()
    assert "Compared with Label" in page1 and "Compared with PKG Drawings" in page1 and "Compared with PCO" in page1
    # The run id is deliberately absent: this sheet goes to BD, and an internal identifier on it is
    # noise to every reader who is not us. The names and the date are what a signed document needs.
    assert "Checked by" in page1 and "Dharma A" in page1
    assert run.metadata.run_id not in page1
    drawings = [d for i in range(len(doc)) for d in doc[i].get_drawings()]
    assert len(drawings) >= outcome.marks
    original = pymupdf.open(bom.path)
    on_the_row = 0
    for i in range(len(doc)):
        words = [pymupdf.Rect(w[:4]) for w in original[i].get_text("words")]
        max_x1 = max(word.x1 for word in words)
        # Marks on component rows only; the legend and the stamp sit above the table.
        row_marks = [d["rect"] for d in doc[i].get_drawings() if d["rect"].width < 12 and d["rect"].y0 > 160]
        for mark in row_marks:
            assert not any(mark.intersects(word) for word in words), f"page {i + 1}: mark at {mark} covers printed text"
        on_the_row += sum(1 for mark in row_marks if mark.x1 < max_x1)
    # The point of the column anchors: marks land inside the table, beside the value they verify,
    # not parked in the right margin past every printed word.
    assert on_the_row >= 30


def test_status_marks_follow_classification(golden_run, tmp_path):
    golden, run = golden_run
    bom = next(d for d in run.documents if d.doc_type is DocType.BOM and d.sku == "1295108FNS")
    outcome = write_annotated(run, bom, tmp_path / "b.pdf")
    kinds = {m.kind for m in outcome.mark_list}
    # Two marks, and only two. A row the comparison could not settle gets no ink, so there is no
    # third kind: on a document that leaves the building, an unsure row is better blank than hedged.
    assert kinds == {"clear", "discrepancy"}
    assert any(m.check == "BOM_LABEL" and m.kind == "discrepancy" and m.item == "2260001" for m in outcome.mark_list)
    assert any(m.check == "PCO_BOM" for m in outcome.mark_list)


def test_a_row_nobody_has_settled_carries_no_mark(golden_run, tmp_path):
    """The rule as a count: marks drawn equal rows decided, not rows checked.

    Labels carry no item number, so a mark cannot be traced back to its row by name. A count can, and
    it reads both ways: the marks missing from an untouched document are exactly the open rows, and
    approving every row brings every one of them back. That second half is the reviewer's promise -
    an approval reaches the document they uploaded.
    """
    golden, run = golden_run
    for doc_type, sku in ((DocType.BOM, "1295108FNS"), (DocType.LABEL, "1175108"), (DocType.DRAWING, "DWG3173108")):
        document = doc_for(run, doc_type, sku)
        rows = [(r, item) for r, item in _rows(run, document) if item.evidence.bbox is not None]
        open_rows = [r for r, _ in rows if _kind(r, None) is None]
        assert open_rows, f"{doc_type.value}: no open rows in the golden set, so this proves nothing"

        undecided = write_annotated(run, document, tmp_path / f"{doc_type.value}.pdf")
        assert len(undecided.mark_list) == len(rows) - len(open_rows), \
            f"{doc_type.value}: {len(undecided.mark_list)} marks for {len(rows) - len(open_rows)} decided rows"

        approved = write_annotated(run, document, tmp_path / f"{doc_type.value}-approved.pdf",
                                   review_states={r.row_id: "clear" for r, _ in rows})
        assert len(approved.mark_list) == len(rows), f"{doc_type.value}: approving every row left one unmarked"
        assert {m.kind for m in approved.mark_list} == {"clear"}


def test_table_bom_falls_back_to_review_page(golden_run, tmp_path):
    golden, run = golden_run
    bom = next(d for d in run.documents if d.doc_type is DocType.BOM and d.sku == "2131910FNS")  # xlsx
    outcome = write_annotated(run, bom, tmp_path / "b.pdf")
    assert outcome.fallback is True
    text = pymupdf.open(outcome.path)[0].get_text()
    assert "no page geometry" in text.lower() and "2131910FNS" in text and "END CAP" in text


@pytest.mark.parametrize("doc_type,sku", [(DocType.BOM, "1295108FNS"), (DocType.LABEL, "1175108"), (DocType.DRAWING, "DWG3173108")])
def test_pdf_without_comparison_boxes_keeps_its_original_pages(golden_run, tmp_path, doc_type, sku):
    _, run = golden_run
    document = doc_for(run, doc_type, sku)
    unpaired = run.model_copy(update={"results": []})
    outcome = write_annotated(unpaired, document, tmp_path / f"unpaired-{doc_type.value}.pdf")
    assert not outcome.fallback and outcome.marks == 0
    with pymupdf.open(document.path) as original, pymupdf.open(outcome.path) as marked:
        assert len(marked) == len(original)
        for before, after in zip(original, marked):
            assert all(line in after.get_text() for line in before.get_text().splitlines() if line.strip())


def test_image_only_pdf_without_boxes_keeps_its_scan(golden_run, tmp_path):
    _, run = golden_run
    drawing = doc_for(run, DocType.DRAWING, "DWG3173108")
    source = tmp_path / "scan.pdf"
    with pymupdf.open(drawing.path) as original, pymupdf.open() as scan:
        image = original[0].get_pixmap(dpi=72)
        page = scan.new_page(width=image.width, height=image.height)
        page.insert_image(page.rect, stream=image.tobytes("png"))
        scan.save(source)
    document = drawing.model_copy(update={"path": str(source), "items": [], "text_lines": []})
    outcome = write_annotated(run.model_copy(update={"results": []}), document, tmp_path / "marked-scan.pdf")
    assert not outcome.fallback and outcome.marks == 0
    with pymupdf.open(source) as original, pymupdf.open(outcome.path) as marked:
        assert len(marked) == len(original) == 1
        assert marked[0].get_pixmap().samples == original[0].get_pixmap().samples


@pytest.mark.parametrize("stamp", ["2026-10-26T23:30:00Z", "2026-10-27T01:30:00+05:30", "2026-10-26T23:30:00"])
def test_marked_date_uses_utc_across_timezone_boundaries(golden_run, stamp):
    assert _updated_on(golden_run[1], stamp) == "26-10-2026"


def test_label_and_drawing_marks_name_the_other_document(golden_run, tmp_path):
    """The colour rule: green means 'the label agrees' whether you hold the BOM or the drawing."""
    golden, run = golden_run
    label = doc_for(run, DocType.LABEL, "1175108")
    drawing = doc_for(run, DocType.DRAWING, "DWG3173108")
    for document, expected in ((label, {"BOM", "DRAWING"}), (drawing, {"BOM", "LABEL"})):
        outcome = write_annotated(run, document, tmp_path / f"{document.doc_type.value}.pdf")
        assert outcome.fallback is False and outcome.marks >= 30
        named = {_other(m.check, document.doc_type.value) for m in outcome.mark_list}
        assert named == expected, f"{document.doc_type.value} marks name {named}, expected {expected}"
        # and the colour on the page really is that document's colour, not just the bookkeeping
        wanted = {tuple(round(v, 2) for v in DOC_COLORS[n]) for n in expected}
        marked, original = pymupdf.open(outcome.path), pymupdf.open(document.path)
        drawn = {tuple(round(v, 2) for v in d["color"]) for i in range(len(marked))
                 for d in added_marks(original, marked, i) if d.get("color")}
        assert drawn == wanted, f"{document.doc_type.value} drew {drawn}, expected {wanted}"


def test_label_and_drawing_marks_never_cover_printed_text(golden_run, tmp_path):
    """A label is a layout, not a table: a mark is 9pt tall and the line above must survive it."""
    golden, run = golden_run
    for document in (doc_for(run, DocType.LABEL, "1175108"), doc_for(run, DocType.DRAWING, "DWG3173108")):
        outcome = write_annotated(run, document, tmp_path / f"clear-{document.doc_type.value}.pdf")
        marked, original = pymupdf.open(outcome.path), pymupdf.open(document.path)
        for i in range(len(marked)):
            words = [pymupdf.Rect(w[:4]) for w in original[i].get_text("words")]
            for mark in added_marks(original, marked, i):
                assert not any(mark["rect"].intersects(w) for w in words), \
                    f"{document.doc_type.value} page {i + 1}: mark at {mark['rect']} covers printed text"
            # every line of the original is still readable text, not flattened by the copy
            for line in original[i].get_text().splitlines():
                assert not line.strip() or line in marked[i].get_text()


def test_only_the_bom_carries_a_legend(golden_run, tmp_path):
    """One key explains all three documents, so the label and drawing need none - as on the real sheets."""
    golden, run = golden_run
    bom = write_annotated(run, doc_for(run, DocType.BOM, "1175108NS"), tmp_path / "b.pdf", checked_by=["Dharma A"])
    assert "Compared with Label" in pymupdf.open(bom.path)[0].get_text()
    for document in (doc_for(run, DocType.LABEL, "1175108"), doc_for(run, DocType.DRAWING, "DWG3173108")):
        out = write_annotated(run, document, tmp_path / f"n-{document.doc_type.value}.pdf", checked_by=["Dharma A"])
        marked, original = pymupdf.open(out.path), pymupdf.open(document.path)
        # No legend and no 'Checked by' block: the one line we add is the date, and page one is the
        # only page that gains anything. (The golden drawing carries its own "Checked by" line, so
        # looking for that string would find the document's own ink, not ours.)
        assert "Compared with" not in marked[0].get_text()
        added = set(marked[0].get_text().split()) - set(original[0].get_text().split())
        assert added == {"Updated", run.metadata.timestamp.strftime("%d-%m-%Y")}, f"{document.doc_type.value}: {added}"
        for i in range(1, len(marked)):
            assert marked[i].get_text() == original[i].get_text(), f"{document.doc_type.value} page {i + 1} gained text"


def test_a_superseded_label_is_never_marked(golden_run, tmp_path):
    """Only the latest label is marked. Its earlier revision is history and earns nothing."""
    golden, run = golden_run
    old = doc_for(run, DocType.LABEL, "1175108", old=True)
    outcome = write_annotated(run, old, tmp_path / "old.pdf")
    assert outcome.marks == 0 and outcome.mark_list == []


def test_marks_do_not_sit_on_each_other(golden_run, tmp_path):
    """A label prints its lines 8.5pt apart, so marks must fit the row pitch, not just the gutter.

    Checking marks against printed words alone is not enough: it let a stacked pair spill across the
    rows above and below, putting 63 of 68 label marks on top of another mark.
    """
    golden, run = golden_run
    for document in (doc_for(run, DocType.LABEL, "1175108"), doc_for(run, DocType.DRAWING, "DWG3173108")):
        outcome = write_annotated(run, document, tmp_path / f"tidy-{document.doc_type.value}.pdf")
        marked, original = pymupdf.open(outcome.path), pymupdf.open(document.path)
        for i in range(len(marked)):
            boxes = [d["rect"] for d in added_marks(original, marked, i)]
            clashes = [(a, b) for x, a in enumerate(boxes) for b in boxes[x + 1:] if a.intersects(b)]
            assert not clashes, f"{document.doc_type.value} page {i + 1}: {len(clashes)} marks overlap another mark"


def test_marks_stay_beside_the_text_they_verify(golden_run, tmp_path):
    """Marks parked past the next text column are clear of everything and say nothing.

    No constant enforces this. A column that would have to travel far has already failed the clearance
    test at that size, so the size drops instead - the marks shrink rather than wander. This test is
    what proves that emergent behaviour holds, since nothing in the code states it.
    """
    golden, run = golden_run
    label = doc_for(run, DocType.LABEL, "1175108")
    outcome = write_annotated(run, label, tmp_path / "near.pdf")
    original = pymupdf.open(label.path)
    ends = {i: sorted(pymupdf.Rect(w[:4]).x1 for w in original[i].get_text("words")) for i in range(len(original))}
    for mark in outcome.mark_list:
        # some printed word on that page must end shortly before the mark starts
        assert any(0 <= mark.x - end <= 3 * COLUMN_MARK for end in ends[mark.page - 1]), \
            f"mark at x={mark.x:.1f} on page {mark.page} is stranded away from any text"


def test_the_screen_key_uses_the_same_colours_as_the_marks():
    """The PDF marks and the on-screen key are written in two languages, so nothing links them.

    A mark wears the colour of the document it was compared against, and the side-by-side page
    explains those colours. Change one list and the legend starts lying about the ink. Python cannot
    import a TSX literal, so this test reads the file and pins the two lists to each other instead.
    """
    page = Path(__file__).parents[2] / "ui/src/pages/MarkedUpPage.tsx"
    on_screen = re.findall(r'colour:\s*"#([0-9A-Fa-f]{6})"', page.read_text())
    assert len(on_screen) == len(MARK_ORDER), f"the key lists {len(on_screen)} colours, MARK_ORDER has {len(MARK_ORDER)}"
    for doc_type, hexed in zip(MARK_ORDER, on_screen):
        drawn = DOC_COLORS[doc_type]
        shown = tuple(int(hexed[i:i + 2], 16) for i in (0, 2, 4))
        # 8-bit hex cannot hold a float exactly, so one count per channel is the closest any
        # honest comparison gets. A real drift moves a channel by tens, not by one.
        off = [abs(round(c * 255) - s) for c, s in zip(drawn, shown)]
        assert max(off) <= 1, f"{doc_type}: the marks are drawn {drawn} but the key shows #{hexed}"


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_the_date_reads_upright_at_the_top_whatever_the_page_rotation(rotation, tmp_path):
    """A real PKG drawing arrives rotated 270, and a rotated page stores its ink unrotated.

    Getting this wrong does not fail loudly - the date simply appears in a corner, or sideways. So the
    test states what a reader sees: near the visual top, reading left to right.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.set_rotation(rotation)
    assert _top_date(page, "Updated 21-10-2026")
    out = tmp_path / f"rot{rotation}.pdf"
    doc.save(out)

    written = pymupdf.open(out)[0]
    words = {w.text: w for w in extract_words(written) if w.text in ("Updated", "21-10-2026")}
    assert set(words) == {"Updated", "21-10-2026"}, f"rotation {rotation}: the date did not survive the save"
    for text, w in words.items():
        assert w.y0 < written.rect.height * 0.1, f"rotation {rotation}: '{text}' is not at the top of the page"
        assert w.x1 - w.x0 > w.y1 - w.y0, f"rotation {rotation}: '{text}' reads sideways"
        assert w.y0 > 0, f"rotation {rotation}: '{text}' sits on the trim edge"


def test_every_document_carries_the_date_of_the_last_decision(golden_run, tmp_path):
    """The date answers 'how current is this?', so it moves with the newest decision, not the run."""
    golden, run = golden_run
    for doc_type, sku in ((DocType.BOM, "1295108FNS"), (DocType.LABEL, "1175108"), (DocType.DRAWING, "DWG3173108")):
        document = doc_for(run, doc_type, sku)
        on_run_date = write_annotated(run, document, tmp_path / f"{doc_type.value}-run.pdf")
        assert run.metadata.timestamp.strftime("%d-%m-%Y") in pymupdf.open(on_run_date.path)[0].get_text(), \
            f"{doc_type.value}: an unreviewed document does not fall back to the run date"

        decided = write_annotated(run, document, tmp_path / f"{doc_type.value}-dec.pdf", updated="2026-10-21T14:03:00")
        text = pymupdf.open(decided.path)[0].get_text()
        assert "21-10-2026" in text, f"{doc_type.value}: the decision date never reached the page"
        assert run.metadata.timestamp.strftime("%d-%m-%Y") not in text, f"{doc_type.value}: the run date is still there too"


def test_an_unsigned_sheet_leaves_the_name_blank_rather_than_making_an_excuse(golden_run, tmp_path):
    """Nobody has signed this run, so the block is a blank for a pen.

    These sheets leave the building. '(reviewer names not recorded)' printed on one is the tool
    explaining itself to a reader who only wants somewhere to write a name.
    """
    golden, run = golden_run
    bom = next(d for d in run.documents if d.doc_type is DocType.BOM and d.sku == "1295108FNS")
    outcome = write_annotated(run, bom, tmp_path / "unsigned.pdf")
    page1 = pymupdf.open(outcome.path)[0].get_text()
    assert "Checked by" in page1, "the heading stays: it says what the blank underneath is for"
    assert "not recorded" not in page1
    assert run.metadata.run_id not in page1


def test_a_two_column_layout_marks_each_item_beside_its_own_words(golden_run, tmp_path):
    """Two items on one line get their marks in two different places, each next to its own text.

    The label lists its contents in two columns. A single shared mark column cannot serve both: the
    widest row in the left column pushes that column's x past the right column's words, so a left
    item's marks land beside the right item's, and one line appears to carry four marks for one item.
    """
    golden, run = golden_run
    label = doc_for(run, DocType.LABEL, "1175108")
    outcome = write_annotated(run, label, tmp_path / "two-column.pdf")
    lines = {}
    for mark in outcome.mark_list:
        lines.setdefault((mark.page, round(mark.y, 1)), []).append(mark.x)
    shared = [sorted(xs) for xs in lines.values() if len(xs) > 2]
    assert shared, "this label must have lines carrying two items, or the test proves nothing"
    for xs in shared:
        # Each item's own pair stays together; the gap to the next item's pair is far wider.
        pair, other = xs[:2], xs[2:]
        assert pair[1] - pair[0] <= COLUMN_MARK + GAP + 0.5, f"a single item's marks drifted apart: {xs}"
        assert other[0] - pair[1] > COLUMN_MARK * 2, f"two items' marks sit together, as if one item: {xs}"

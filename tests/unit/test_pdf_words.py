import pymupdf
import pytest

from kaizen.ingest.pdf_words import (
    ColumnBand,
    assign_columns,
    extract_annotations,
    extract_words,
    group_lines,
    line_bbox,
    line_text,
)


@pytest.fixture
def two_line_page(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=200)
    page.insert_text((20, 50), "0396447", fontsize=8)
    page.insert_text((120, 50), "ABSORBENT TOWEL", fontsize=8)
    page.insert_text((300, 50), "1.0000", fontsize=8)
    page.insert_text((20, 80), "5167473", fontsize=8)
    page.insert_text((120, 80), "TAPE ANCHOR PER-Q-CATH", fontsize=8)
    page.insert_text((300, 80), "2.0000", fontsize=8)
    annot = page.add_freetext_annot(pymupdf.Rect(300, 84, 360, 96), "0.4000")
    annot.update()
    path = tmp_path / "two_lines.pdf"
    doc.save(path)
    doc.close()
    return path


def test_extract_words_returns_bboxes_sorted_by_position(two_line_page):
    doc = pymupdf.open(two_line_page)
    words = extract_words(doc[0])
    assert [w.text for w in words][:3] == ["0396447", "ABSORBENT", "TOWEL"]
    first = words[0]
    assert first.x0 < first.x1 and first.y0 < first.y1
    assert first.x0 == pytest.approx(20, abs=1.5)


def test_group_lines_by_vertical_position(two_line_page):
    doc = pymupdf.open(two_line_page)
    lines = group_lines(extract_words(doc[0]))
    assert len(lines) == 2
    assert line_text(lines[0]) == "0396447 ABSORBENT TOWEL 1.0000"
    assert line_text(lines[1]) == "5167473 TAPE ANCHOR PER-Q-CATH 2.0000"
    box = line_bbox(lines[0])
    assert box.x0 == pytest.approx(20, abs=1.5) and box.x1 > 300


def test_assign_columns_uses_band_containing_word_center(two_line_page):
    doc = pymupdf.open(two_line_page)
    lines = group_lines(extract_words(doc[0]))
    bands = [ColumnBand("item", 0, 110), ColumnBand("description", 110, 290), ColumnBand("qty", 290, 400)]
    cols = assign_columns(lines[1], bands)
    assert [w.text for w in cols["item"]] == ["5167473"]
    assert " ".join(w.text for w in cols["description"]) == "TAPE ANCHOR PER-Q-CATH"
    assert [w.text for w in cols["qty"]] == ["2.0000"]


def test_assign_columns_falls_back_to_nearest_band_for_out_of_range_word():
    from kaizen.ingest.pdf_words import Word

    bands = [ColumnBand("a", 100, 200), ColumnBand("b", 300, 400)]
    stray = Word(text="x", x0=250, y0=0, x1=260, y1=10, block=0, line=0, word_no=0)
    cols = assign_columns([stray], bands)
    assert cols["a"] == [stray] or cols["b"] == [stray]


def test_extract_annotations_returns_freetext_with_rect(two_line_page):
    doc = pymupdf.open(two_line_page)
    annots = extract_annotations(doc[0])
    assert len(annots) == 1
    assert annots[0].content == "0.4000"
    assert annots[0].type == "FreeText"
    assert annots[0].y0 == pytest.approx(84, abs=1.0)


def test_annotation_text_is_not_extracted_as_page_words(two_line_page):
    doc = pymupdf.open(two_line_page)
    texts = [w.text for w in extract_words(doc[0])]
    assert "0.4000" not in texts
    assert "0.4000" in [w.text for w in extract_words(doc[0], exclude_annotation_text=False)]


def test_split_line_by_gaps_separates_columns_at_same_height():
    from kaizen.ingest.pdf_words import Word, split_line_by_gaps

    words = [Word("END", 40, 100, 52, 107, 0, 0, 0), Word("CAPS", 54, 100, 70, 107, 0, 0, 1), Word("SYRINGES", 615, 100, 650, 107, 0, 0, 2)]
    frags = split_line_by_gaps(words, gap=18)
    assert [[w.text for w in f] for f in frags] == [["END", "CAPS"], ["SYRINGES"]]

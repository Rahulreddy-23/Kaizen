import openpyxl
import pytest

from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.ingest.detect import detect_doc_type, parse_document
from kaizen.ingest.grouping import family_of, group_by_sku
from kaizen.models import DocType


@pytest.fixture
def docs(tmp_path):
    bom = render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "sku-001" / "bom_1295108NS.pdf")
    label = render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), tmp_path / "sku-001" / "label_1295108.pdf")
    return bom, label


def test_detect_by_content(docs):
    bom, label = docs
    assert detect_doc_type(bom) is DocType.BOM
    assert detect_doc_type(label) is DocType.LABEL


def test_detect_xlsx_bom(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.append(["Component Item", "Component Description", "Quantity Per"])
    path = tmp_path / "anything.xlsx"
    wb.save(path)
    assert detect_doc_type(path) is DocType.BOM


def test_detect_falls_back_to_filename(tmp_path):
    path = tmp_path / "some_drawing.pdf"
    import pymupdf

    d = pymupdf.open()
    d.new_page()
    d.save(path)
    assert detect_doc_type(path) is DocType.DRAWING
    assert detect_doc_type(tmp_path / "notes.txt") is None


def test_parse_document_dispatches(docs):
    bom, label = docs
    assert parse_document(bom).document.doc_type is DocType.BOM
    assert parse_document(label).document.doc_type is DocType.LABEL


def test_parse_document_reports_unsupported_types(tmp_path):

    path = tmp_path / "unit_label_scan.csv"  # a label that is not a PDF (image/OCR path is not implemented)
    path.write_text("REF,1295108\nContents,1 Each - Towel\n")
    outcome = parse_document(path)
    assert outcome.document is None
    assert "NOT IMPLEMENTED" in outcome.reason


@pytest.mark.parametrize("code, family", [("1295108NS", "1295108"), ("1295108FNS", "1295108"), ("1295108", "1295108"), ("ABC123", "ABC123"), ("2131910NS", "2131910")])
def test_family_of(code, family):
    assert family_of(code) == family


def test_group_by_folder_when_sets_are_in_folders(tmp_path):
    bom1 = parse_document(render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "sku-001" / "bom.pdf")).document
    lab1 = parse_document(render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), tmp_path / "sku-001" / "label.pdf")).document
    bom2 = parse_document(render_bom_pdf(BomSpec(parent_item="1395108QNS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "sku-002" / "bom.pdf")).document
    lab2 = parse_document(render_label_pdf(LabelSpec(ref="9999999", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), tmp_path / "sku-002" / "label.pdf")).document
    groups = group_by_sku([bom1, lab1, bom2, lab2])
    assert [g.sku for g in groups] == ["1295108NS", "1395108QNS"]
    assert groups[0].document_ids == [bom1.id, lab1.id]
    assert groups[0].warnings == []
    # sku-002's label REF does not belong to the BOM family: grouped together by folder, flagged for the check
    assert groups[1].document_ids == [bom2.id, lab2.id]
    assert any("9999999" in w for w in groups[1].warnings)


def test_group_by_family_when_files_are_flat(tmp_path):
    bom = parse_document(render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "bom_a.pdf")).document
    lab = parse_document(render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), tmp_path / "label_a.pdf")).document
    lonely = parse_document(render_bom_pdf(BomSpec(parent_item="7770001NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "bom_b.pdf")).document
    groups = group_by_sku([bom, lab, lonely])
    by_sku = {g.sku: g for g in groups}
    assert by_sku["1295108NS"].document_ids == [bom.id, lab.id]
    assert by_sku["1295108NS"].family == "1295108"
    assert any("no label" in w.lower() for w in by_sku["7770001NS"].warnings)

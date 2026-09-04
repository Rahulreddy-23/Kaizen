from decimal import Decimal

import pytest

from kaizen.datasets.pdf_bom import AnnotationSpec, BomRowSpec, BomSpec, render_bom_pdf
from kaizen.ingest.bom_pdf import PARSER_NAME, parse_bom_pdf
from kaizen.models import DocType, ItemCategory

BRIEF_ROWS = [
    BomRowSpec(item="0703450", description="LOD THERMAL TRANSFER RIBBON", qty_per="0.0000", ext_qty="0.000000", t="P", oper_seq="5.00"),
    BomRowSpec(item="BAW0722153", description="EN LOD, CASE LABEL", qty_per="0.4000", ext_qty="0.400000", t="Q", eff_from="02/10/15", oper_seq="5.00"),
    BomRowSpec(item="BAW0724416", description="EN LOD, UNIT LABEL", qty_per="1.0000", ext_qty="1.000000", t="Q", eff_from="08/09/10", oper_seq="5.00"),
    BomRowSpec(item="C293054", description="LABEL, PRIMING VOLUME, BLANK", qty_per="1.0000", ext_qty="1.046000", eff_from="01/22/16", oper_seq="5.00"),
    BomRowSpec(item="MPS0090", description="PRODUCING LABELS ON THE", qty_per="0.0000", ext_qty="0.000000", t="Q", oper_seq="5.00"),
    BomRowSpec(item="PK0722294", description="CASE LABEL, BLANK", qty_per="0.4000", ext_qty="0.400000", eff_from="02/10/15", oper_seq="5.00"),
    BomRowSpec(item="PK0756181", description="PORT ACCESS KIT LABEL STOCK", qty_per="1.0000", ext_qty="1.000000", eff_from="01/23/18", oper_seq="5.00"),
    BomRowSpec(item="FM00182", description="FIRST/LAST LABEL RECORD", qty_per="0.0000", ext_qty="0.000000", t="Q", oper_seq="6.00"),
    BomRowSpec(item="MPS0019", description="PACKAGING QUALITY", qty_per="0.0000", ext_qty="0.000000", t="Q", oper_seq="6.00"),
    BomRowSpec(item="0396447", description="ABSORBENT TOWEL", qty_per="1.0000", ext_qty="1.001000", oper_seq="7.00"),
    BomRowSpec(item="5167473", description="TAPE ANCHOR PER-Q-CATH", qty_per="1.0000", ext_qty="1.006000", oper_seq="7.00"),
    BomRowSpec(item="7770001", description="GAUZE 4X4", qty_per="10.0000", ext_qty="10.000000", eff_thru="12/31/20", oper_seq="7.00"),
]


@pytest.fixture
def brief_bom(tmp_path):
    spec = BomSpec(
        parent_item="2131910NS",
        parent_description="PRT ACCESS KIT W/PWRLOC",
        branch_plant="5150",
        as_of_date="09/03/25",
        rows=BRIEF_ROWS,
    )
    return render_bom_pdf(spec, tmp_path / "bom.pdf")


def test_header_fields(brief_bom):
    doc = parse_bom_pdf(brief_bom)
    assert doc.doc_type is DocType.BOM
    assert doc.parser_name == PARSER_NAME
    assert doc.sku == "2131910NS"
    assert doc.header["parent_description"] == "PRT ACCESS KIT W/PWRLOC"
    assert doc.header["branch_plant"] == "5150"
    assert doc.header["as_of_date"] == "09/03/25"
    assert doc.header["type"] == "M"
    assert len(doc.sha256) == 64


def test_rows_parsed_with_quantities_and_categories(brief_bom):
    doc = parse_bom_pdf(brief_bom)
    by_item = {i.item_number: i for i in doc.items}
    assert len(doc.items) == len(BRIEF_ROWS)
    towel = by_item["0396447"]
    assert towel.description == "ABSORBENT TOWEL"
    assert towel.quantity == Decimal("1.0000")
    assert towel.uom == "EA"
    assert towel.oper_seq == "7.00"
    assert towel.category is ItemCategory.PHYSICAL_COMPONENT
    assert by_item["BAW0722153"].quantity == Decimal("0.4000")
    assert by_item["BAW0722153"].category is ItemCategory.LABEL
    assert by_item["MPS0090"].category is ItemCategory.PROCESS
    assert by_item["FM00182"].category is ItemCategory.QUALITY
    assert by_item["C293054"].description == "LABEL, PRIMING VOLUME, BLANK"
    assert by_item["7770001"].attributes["ext_qty"] == "10.000000"
    assert by_item["7770001"].attributes["effective_from"] == "12/11/09"


def test_expired_row_is_inactive(brief_bom):
    doc = parse_bom_pdf(brief_bom)
    by_item = {i.item_number: i for i in doc.items}
    assert by_item["7770001"].is_active is False
    assert by_item["0396447"].is_active is True


def test_evidence_retained(brief_bom):
    doc = parse_bom_pdf(brief_bom)
    towel = next(i for i in doc.items if i.item_number == "0396447")
    assert towel.evidence.page == 1
    assert towel.evidence.bbox is not None
    assert "0396447" in towel.evidence.raw_text and "ABSORBENT TOWEL" in towel.evidence.raw_text
    assert towel.evidence.file_sha256 == doc.sha256
    assert towel.sku == "2131910NS"
    assert towel.doc_id == doc.id


def test_multipage_rows_keep_page_numbers(tmp_path):
    rows = [BomRowSpec(item=f"{2000000 + i}", description=f"PART NUMBER {i}") for i in range(30)]
    path = render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=rows), tmp_path / "b.pdf", rows_per_page=12)
    doc = parse_bom_pdf(path)
    assert len(doc.items) == 30
    assert doc.items[0].evidence.page == 1
    assert doc.items[29].evidence.page == 3
    assert doc.items[29].item_number == "2000029"


def test_freetext_annotation_captured_as_redline(tmp_path):
    spec = BomSpec(parent_item="1295108NS", parent_description="KIT", rows=BRIEF_ROWS[:3])
    spec.annotations = [AnnotationSpec(row_index=1, field="component_item", text="PK0722294")]
    path = render_bom_pdf(spec, tmp_path / "b.pdf")
    doc = parse_bom_pdf(path)
    row = doc.items[1]
    assert row.attributes["redlines"] == [{"field": "component_item", "text": "PK0722294"}]
    assert doc.items[0].attributes.get("redlines", []) == []


def test_unparseable_quantity_lowers_confidence_and_warns(tmp_path):
    rows = [BomRowSpec(item="1234567", description="ODD ROW", qty_per="n/a")]
    path = render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=rows), tmp_path / "b.pdf")
    doc = parse_bom_pdf(path)
    assert doc.items[0].quantity is None
    assert doc.items[0].extraction_confidence < 1.0
    assert any("quantity" in w.lower() for w in doc.warnings)

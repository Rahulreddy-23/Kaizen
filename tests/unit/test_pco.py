from decimal import Decimal

import pytest

from kaizen.datasets.pco_docs import PcoRowSpec, PcoSpec, render_pco_pdf, write_pco_xlsx
from kaizen.ingest.detect import detect_doc_type, parse_document
from kaizen.ingest.pco import PARSER_NAME, parse_pco
from kaizen.models import DocType

ROWS = [
    PcoRowSpec(item_actual="RM5002565", item_proposed="DELETE", description="SCISSORS WITH PROTECTOR TUBING"),
    PcoRowSpec(item_actual="", item_proposed="RM0737876", description="CATHETER TRIMMING DEVICE", qty_proposed="1", seq_proposed="7"),
    PcoRowSpec(item_actual="", item_proposed="PK0744425", description="IFU, CATH TRIMMING DEVICE", qty_proposed="1", seq_proposed="7"),
    PcoRowSpec(item_actual="0396447", item_proposed="0396448", description="ABSORBENT TOWEL LARGE", qty_actual="1", qty_proposed="1", seq_actual="7", seq_proposed="7"),
    PcoRowSpec(item_actual="2260001", item_proposed="2260001", description="END CAP", qty_actual="2", qty_proposed="3", seq_actual="7", seq_proposed="7"),
]
CODES = ["1175108NS", "1275108NS", "1295108FNS", "1295108NS", "1395108QNS", "9295108FNS"]


@pytest.fixture(params=["xlsx", "pdf"])
def pco_file(request, tmp_path):
    spec = PcoSpec(pco_number="PCO34590", revision="0", branch="5150", affected_codes=CODES, rows=ROWS)
    if request.param == "xlsx":
        return write_pco_xlsx(spec, tmp_path / "pco.xlsx")
    return render_pco_pdf(spec, tmp_path / "pco.pdf")


def test_detects_pco(pco_file):
    assert detect_doc_type(pco_file) is DocType.PCO
    assert parse_document(pco_file).document.doc_type is DocType.PCO


def test_header_and_affected_codes(pco_file):
    doc = parse_pco(pco_file)
    assert doc.parser_name == PARSER_NAME
    assert doc.header["pco_number"] == "PCO34590"
    assert doc.header["revision"] == "0"
    assert doc.header["branch"] == "5150"
    assert doc.header["change_type"] == "Change"
    assert doc.header["bill_type"] == "M"
    assert doc.header["affected_codes"] == CODES
    codes = [i for i in doc.items if i.attributes.get("kind") == "affected_code"]
    assert [c.item_number for c in codes] == CODES
    assert all(c.evidence.locator for c in codes)


def test_change_rows_with_kinds(pco_file):
    doc = parse_pco(pco_file)
    changes = [i for i in doc.items if i.attributes.get("kind") == "change"]
    kinds = [(c.attributes["change_kind"], c.attributes["item_actual"], c.attributes["item_proposed"]) for c in changes]
    assert kinds == [
        ("DELETE", "RM5002565", ""),
        ("ADD", "", "RM0737876"),
        ("ADD", "", "PK0744425"),
        ("SUBSTITUTE", "0396447", "0396448"),
        ("MODIFY", "2260001", "2260001"),
    ]
    add = changes[1]
    assert add.item_number == "RM0737876" and add.description == "CATHETER TRIMMING DEVICE"
    assert add.quantity == Decimal("1") and add.oper_seq == "7"
    delete = changes[0]
    assert delete.item_number == "RM5002565" and delete.quantity is None
    modify = changes[4]
    assert modify.attributes["qty_actual"] == "2" and modify.attributes["qty_proposed"] == "3"
    assert all(c.evidence.raw_text for c in changes)


def test_pdf_rows_carry_page_and_bbox(tmp_path):
    spec = PcoSpec(pco_number="PCO1", revision="1", branch="5150", affected_codes=CODES[:2], rows=ROWS[:2])
    doc = parse_pco(render_pco_pdf(spec, tmp_path / "p.pdf"))
    change = [i for i in doc.items if i.attributes.get("kind") == "change"][0]
    assert change.evidence.page == 1 and change.evidence.bbox is not None


def test_empty_pco_warns(tmp_path):
    spec = PcoSpec(pco_number="PCO2", revision="0", branch="5150", affected_codes=[], rows=[])
    doc = parse_pco(write_pco_xlsx(spec, tmp_path / "e.xlsx"))
    assert doc.items == []
    assert any("affected" in w.lower() for w in doc.warnings)

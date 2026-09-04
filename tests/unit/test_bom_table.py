import csv
from decimal import Decimal

import openpyxl
import pytest

from kaizen.ingest.bom_table import PARSER_NAME, parse_bom_table
from kaizen.models import DocType, ItemCategory

HEADER = ["Level", "Component Item", "Component Description", "Branch/Plant", "Quantity Per", "Ext Qty", "UM", "T", "Effective From", "Effective Thru", "Oper Seq No"]
ROWS = [
    [1, "0396447", "ABSORBENT TOWEL", "5150", 1.0, 1.001, "EA", "P", "12/11/09", "12/31/40", "7.00"],
    [1, "BAW0722153", "EN LOD, CASE LABEL", "5150", 0.4, 0.4, "EA", "Q", "02/10/15", "12/31/40", "5.00"],
    [1, "5167473", "TAPE ANCHOR PER-Q-CATH", "5150", "2.0000", "2.000000", "EA", "P", "12/11/09", "12/31/20", "7.00"],
]


@pytest.fixture
def xlsx_bom(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BOM"
    ws.append(["Bill of Material Print"])
    ws.append(["Parent Item", "1295108NS", None, "Parent Description", "POWERPICC SOLO2 KIT"])
    ws.append(["Branch/Plant", "5150", None, "As of Date", "09/03/25"])
    ws.append([])
    ws.append(HEADER)
    for r in ROWS:
        ws.append(r)
    path = tmp_path / "bom.xlsx"
    wb.save(path)
    return path


def test_xlsx_header_and_rows(xlsx_bom):
    doc = parse_bom_table(xlsx_bom)
    assert doc.doc_type is DocType.BOM
    assert doc.parser_name == PARSER_NAME
    assert doc.sku == "1295108NS"
    assert doc.header["parent_description"] == "POWERPICC SOLO2 KIT"
    assert doc.header["as_of_date"] == "09/03/25"
    assert [i.item_number for i in doc.items] == ["0396447", "BAW0722153", "5167473"]
    towel = doc.items[0]
    assert towel.quantity == Decimal("1.0")
    assert towel.category is ItemCategory.PHYSICAL_COMPONENT
    assert towel.oper_seq == "7.00"
    assert doc.items[1].quantity == Decimal("0.4")
    assert doc.items[1].category is ItemCategory.LABEL
    assert doc.items[2].is_active is False


def test_xlsx_evidence_points_to_sheet_row(xlsx_bom):
    doc = parse_bom_table(xlsx_bom)
    ev = doc.items[0].evidence
    assert ev.page is None
    assert ev.sheet == "BOM"
    assert ev.locator == "sheet 'BOM', row 6"
    assert "ABSORBENT TOWEL" in ev.raw_text
    assert ev.file_sha256 == doc.sha256


def test_csv_with_alias_headers(tmp_path):
    path = tmp_path / "bom.csv"
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Parent Item", "1295108FNS"])
        w.writerow(["Item Number", "Description", "Qty Per", "UOM", "Oper Seq"])
        w.writerow(["0396447", "ABSORBENT TOWEL", "1", "EA", "7.00"])
        w.writerow(["MPS0090", "PRODUCING LABELS ON THE", "0", "EA", "5.00"])
    doc = parse_bom_table(path)
    assert doc.sku == "1295108FNS"
    assert len(doc.items) == 2
    assert doc.items[0].quantity == Decimal("1")
    assert doc.items[1].category is ItemCategory.PROCESS
    assert doc.items[0].evidence.locator == "sheet 'bom.csv', row 3"


def test_missing_header_row_warns_and_yields_no_items(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.append(["nothing", "useful"])
    path = tmp_path / "junk.xlsx"
    wb.save(path)
    doc = parse_bom_table(path)
    assert doc.items == []
    assert any("header" in w.lower() for w in doc.warnings)

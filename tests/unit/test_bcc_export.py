"""BD's BOM cross-check (BCC) template: Label VS BOM, Drawings VS BOM and Combined sheets."""

import pytest

from kaizen.datasets.drawing_docs import CalloutSpec, DrawingSpec, render_drawing_pdf
from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.pipeline import run_folder
from kaizen.reporting.bcc import bcc_workbook
from kaizen.reporting.excel import ReviewBundle
from kaizen.terminology.store import RelationshipStore

LABEL_HEADERS = ["S.No", "Label Description", "Label Qty", "BOM Component No", "BOM Description", "BOM Qty", "Description Match", "Qty Match", "Remarks"]
DRAWING_HEADERS = ["S.No", "Drawing Description", "BOM Component No", "BOM Description", "BOM Qty", "Description Match", "Remarks"]
COMBINED_HEADERS = ["S.No", "Label Description", "Drawing Description", "BOM Description", "BOM Component No", "Label VS BOM Description",
                    "Drawing VS BOM Description", "Description Match", "Label Qty", "BOM Qty", "Qty Match", "Status", "Remarks", "Time stamp",
                    "Approved By Facilitator", "Approved by IR"]


@pytest.fixture
def run(tmp_path):
    kit = tmp_path / "kit"
    rows = [BomRowSpec(item="2260001", description="END CAP", qty_per="2"), BomRowSpec(item="2260002", description="SYRINGE, 10ML", qty_per="1"),
            BomRowSpec(item="2260003", description="MASK", qty_per="1"), BomRowSpec(item="LAB1234567", description="EN LOD, UNIT LABEL", qty_per="1"),
            BomRowSpec(item="DWG1234567", description="TRAY ASSEMBLY", qty_per="0")]
    render_bom_pdf(BomSpec(parent_item="1234567NS", parent_description="KIT", rows=rows), kit / "bom.pdf")
    render_label_pdf(LabelSpec(ref="1234567", product_name="Kit", contents=["2 Each - End Cap", "3 Each - Syringe, 10 mL", "1 Each - Gauze"]), kit / "label.pdf")
    render_drawing_pdf(DrawingSpec(drawing_number="DWG1234567", revision="A", title="TRAY ASSEMBLY", plant="TEST",
                                   callouts=[CalloutSpec("END CAP", "TAPÓN"), CalloutSpec("SYRINGE", "JERINGA")]), kit / "drawing.pdf")
    return run_folder(kit, RelationshipStore.default())


def values(ws):
    return [[cell.value for cell in row] for row in ws.iter_rows()]


def table(ws, headers):
    rows = values(ws)
    start = next(i for i, row in enumerate(rows) if row[:len(headers)] == headers)
    body = []
    for row in rows[start + 1:]:
        if isinstance(row[0], int):
            body.append(dict(zip(headers, row)))
        elif body or row[0] is not None:
            break  # the table ends; a totals line may sit between the header and the first row
    return body


def metrics(ws):
    rows = values(ws)
    start = next(i for i, row in enumerate(rows) if row[1:3] == ["Metric", "Count"])
    return {row[1]: row[2] for row in rows[start + 1:] if row[1]}


def test_single_sku_run_uses_the_three_template_sheets(run):
    wb = bcc_workbook(run)
    assert wb.sheetnames == ["Label VS BOM", "Drawings VS BOM", "Combined"]
    label = table(wb["Label VS BOM"], LABEL_HEADERS)
    end_cap = next(r for r in label if r["Label Description"] == "End Cap")
    assert (end_cap["BOM Component No"], end_cap["Label Qty"], end_cap["BOM Qty"], end_cap["Description Match"], end_cap["Qty Match"]) == ("2260001", 2, 2, "Exact match", "Exact match")
    syringe = next(r for r in label if r["BOM Component No"] == "2260002")
    assert syringe["Qty Match"] == "No match" and "3" in syringe["Remarks"]
    assert next(r for r in label if r["Label Description"] == "Gauze")["Description Match"] == "Missing data in BOM"
    assert next(r for r in label if r["BOM Component No"] == "2260003")["Description Match"] == "Missing data in Label"
    assert [r["S.No"] for r in label] == list(range(1, len(label) + 1))
    assert metrics(wb["Label VS BOM"]) == {"Total Label Components": 3, "Components Found in BOM": 5, "Label components found in BOM": 2,
                                           "Description Mismatches": 2, "Qty Mismatches": 1, "Fully Matched Components": 1}


def test_drawing_sheet_compares_callouts_with_the_bom(run):
    wb = bcc_workbook(run)
    drawing = table(wb["Drawings VS BOM"], DRAWING_HEADERS)
    assert {r["Drawing Description"]: r["BOM Component No"] for r in drawing if r["Drawing Description"]} == {"END CAP": "2260001", "SYRINGE": "2260002"}
    found = metrics(wb["Drawings VS BOM"])
    assert (found["Total Drawing Components"], found["Total Components Found in BOM"], found["Drawing components found in BOM"]) == (2, 5, 2)


def test_combined_sheet_names_the_documents_and_joins_each_bom_component(run):
    wb = bcc_workbook(run)
    rows = values(wb["Combined"])
    assert rows[0][0] == "SKU Number - 1234567NS (BOM Parent Item number)"
    assert rows[1][0] == "Label Part number - LAB1234567 (Label part number)"
    assert rows[2][0] == "Drawing Number - DWG1234567 Rev A (Drawing number)"
    assert rows[3] == COMBINED_HEADERS
    assert rows[4][1:4] == ["Total components = 3", "Total components = 2", "Total components = 5"]
    combined = table(wb["Combined"], COMBINED_HEADERS)
    end_cap = next(r for r in combined if r["BOM Component No"] == "2260001")
    assert (end_cap["Label Description"], end_cap["Drawing Description"], end_cap["Label VS BOM Description"], end_cap["Drawing VS BOM Description"]) == ("End Cap", "END CAP", "Exact match", "Exact match")
    assert end_cap["Description Match"] == "Exact match" and end_cap["Status"] == "Cleared by engine"
    mask = next(r for r in combined if r["BOM Component No"] == "2260003")
    assert mask["Description Match"] == "Missing data in Label" and mask["Status"] == "Not reviewed"
    assert any(r["Label Description"] == "Gauze" and r["BOM Component No"] is None for r in combined)


def test_reviewer_approval_fills_status_and_names(run):
    row = next(r for r in run.results if r.check.value == "BOM_LABEL" and r.source_a and r.source_a.item_number == "2260001")
    final = type("Final", (), {"final_decision": "ACCEPT", "finalized_by": "approver@bd.com", "finalized_at": "2026-11-02T10:00:00+00:00", "note": ""})()
    decision = type("Decision", (), {"decision": "ACCEPT", "reviewer": "facilitator@bd.com", "decided_at": "2026-11-02T09:00:00+00:00", "comment": "Matches", "override_classification": None})()
    wb = bcc_workbook(run, ReviewBundle(decisions={row.row_id: {1: decision}}, finals={row.row_id: final}))
    end_cap = next(r for r in table(wb["Combined"], COMBINED_HEADERS) if r["BOM Component No"] == "2260001")
    assert (end_cap["Approved By Facilitator"], end_cap["Approved by IR"]) == ("facilitator@bd.com", "approver@bd.com")
    assert end_cap["Status"] == "Approved" and end_cap["Time stamp"] == "2026-11-02 10:00 UTC"

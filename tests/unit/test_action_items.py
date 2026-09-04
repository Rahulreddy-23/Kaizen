"""Action items from confirmed discrepancies; verify & close across runs via stable comparison keys."""

import pytest

from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.models import Classification, Thresholds
from kaizen.pipeline import run_folder, save_run
from kaizen.review.action_items import ActionItemStore, comparison_key
from kaizen.review.store import ReviewStore
from kaizen.workspace import Workspace


def _dataset(root, end_cap_qty="2.0000"):
    render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL"), BomRowSpec(item="2260001", description="END CAP", qty_per=end_cap_qty)]), root / "sku-001" / "bom.pdf")
    render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - Towel, Absorbent", "1 Each - End Cap"]), root / "sku-001" / "label.pdf")
    return root


@pytest.fixture
def ws(tmp_path):
    return Workspace(tmp_path / "ws")


def _run(ws, folder):
    run = run_folder(folder, ws.repository.store(), Thresholds())
    path = save_run(run, ws.runs_dir / run.metadata.run_id / "run.json")
    ws.register_run(run, path)
    return run


def test_comparison_key_is_stable_across_runs_and_independent_of_row_ids(tmp_path, ws):
    run1 = _run(ws, _dataset(tmp_path / "a"))
    run2 = _run(ws, _dataset(tmp_path / "b"))
    r1 = next(r for r in run1.results if r.source_a and r.source_a.item_number == "2260001")
    r2 = next(r for r in run2.results if r.source_a and r.source_a.item_number == "2260001")
    assert comparison_key(r1) == comparison_key(r2)
    assert "2260001" in comparison_key(r1) and "BOM_LABEL" in comparison_key(r1) and "1295108NS" in comparison_key(r1)


def test_confirmed_discrepancy_creates_action_item_linked_to_row(tmp_path, ws):
    run = _run(ws, _dataset(tmp_path / "a"))
    row = next(r for r in run.results if r.classification is Classification.MISMATCH)
    review = ReviewStore(ws.db)
    items = ActionItemStore(ws.db)
    review.decide(run.metadata.run_id, row.row_id, slot=1, reviewer="Dharma", decision="CONFIRM_DISCREPANCY", comment="BOM qty is wrong")
    ai = items.create_from_result(run, row, reviewer="Dharma", owner="R&D")
    assert ai.id.startswith("AI-") and ai.run_id == run.metadata.run_id and ai.row_id == row.row_id
    assert ai.sku == "1295108NS" and ai.check_type == "BOM_LABEL" and ai.discrepancy_type == "QTY_MISMATCH" and ai.severity == "MAJOR"
    assert ai.status == "OPEN" and ai.owner == "R&D" and ai.recommended_action and ai.comparison_key == comparison_key(row)
    assert items.get(ai.id).detail == row.discrepancies[0].detail
    assert items.for_run(run.metadata.run_id)[0].id == ai.id


def test_verify_and_close_resolves_when_rerun_no_longer_shows_the_discrepancy(tmp_path, ws):
    run1 = _run(ws, _dataset(tmp_path / "a"))
    row = next(r for r in run1.results if r.classification is Classification.MISMATCH)
    items = ActionItemStore(ws.db)
    ai = items.create_from_result(run1, row, reviewer="Dharma", owner="R&D")
    still_open = _run(ws, _dataset(tmp_path / "b"))  # nothing corrected
    outcome = items.verify_and_close(still_open)
    assert outcome.resolved == [] and items.get(ai.id).status == "OPEN"
    corrected = _run(ws, _dataset(tmp_path / "c", end_cap_qty="1.0000"))
    outcome = items.verify_and_close(corrected)
    assert outcome.resolved == [ai.id]
    resolved = items.get(ai.id)
    assert resolved.status == "RESOLVED" and resolved.resolved_in_run == corrected.metadata.run_id
    assert outcome.still_open == []


def test_verify_and_close_ignores_runs_that_do_not_cover_the_sku(tmp_path, ws):
    run1 = _run(ws, _dataset(tmp_path / "a"))
    row = next(r for r in run1.results if r.classification is Classification.MISMATCH)
    items = ActionItemStore(ws.db)
    ai = items.create_from_result(run1, row, reviewer="Dharma", owner="R&D")
    other = tmp_path / "other"
    render_bom_pdf(BomSpec(parent_item="7770001NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), other / "sku-x" / "bom.pdf")
    render_label_pdf(LabelSpec(ref="7770001", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), other / "sku-x" / "label.pdf")
    outcome = items.verify_and_close(_run(ws, other))
    assert outcome.resolved == [] and outcome.not_covered == [ai.id]
    assert items.get(ai.id).status == "OPEN"


def test_update_status_and_owner(tmp_path, ws):
    run = _run(ws, _dataset(tmp_path / "a"))
    row = next(r for r in run.results if r.classification is Classification.MISMATCH)
    items = ActionItemStore(ws.db)
    ai = items.create_from_result(run, row, reviewer="Dharma", owner="R&D")
    items.update(ai.id, status="IN_PROGRESS", owner="Quality", by="Hemant")
    assert items.get(ai.id).status == "IN_PROGRESS" and items.get(ai.id).owner == "Quality"
    with pytest.raises(ValueError):
        items.update(ai.id, status="DONE-ISH", by="x")

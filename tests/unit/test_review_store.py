"""Phase 6 review layer: decisions never overwrite engine recommendations; states and history are explicit."""

import pytest

from kaizen.datasets.build import build_golden
from kaizen.models import Classification, Thresholds
from kaizen.pipeline import run_folder, save_run
from kaizen.review.store import ReviewStore
from kaizen.workspace import Workspace


@pytest.fixture(scope="module")
def ws_and_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("d")
    golden = build_golden(root / "golden")
    ws = Workspace(root / "ws")
    run = run_folder(golden / "sku-002", ws.repository.store(), Thresholds())
    path = save_run(run, ws.runs_dir / run.metadata.run_id / "run.json")
    ws.register_run(run, path)
    return ws, run


@pytest.fixture
def store(ws_and_run):
    ws, run = ws_and_run
    s = ReviewStore(ws.db)
    s.clear_run(run.metadata.run_id)
    return s


def _row(run, classification=None, with_discrepancy=None):
    for r in run.results:
        if r.role != "item":
            continue
        if classification and r.classification is not classification:
            continue
        if with_discrepancy and not any(d.type.value == with_discrepancy for d in r.discrepancies):
            continue
        return r
    raise AssertionError("no such row")


def test_engine_recommendation_is_preserved_when_reviewer_overrides(ws_and_run, store):
    ws, run = ws_and_run
    row = _row(run, Classification.POTENTIAL)
    store.decide(run.metadata.run_id, row.row_id, slot=1, reviewer="Dharma", decision="OVERRIDE", override_classification="EQUIVALENT", comment="same part")
    view = store.row_state(run.metadata.run_id, row.row_id)
    assert view.state == "REVIEWER_1_COMPLETE"
    assert view.decisions[1].decision == "OVERRIDE" and view.decisions[1].override_classification == "EQUIVALENT"
    assert row.classification is Classification.POTENTIAL  # engine result untouched
    assert view.effective_classification == "EQUIVALENT"


def test_states_progress_and_disagreement_is_detected(ws_and_run, store):
    ws, run = ws_and_run
    rid = run.metadata.run_id
    row = _row(run, Classification.MISMATCH)
    assert store.row_state(rid, row.row_id).state == "ENGINE_RECOMMENDED"
    store.decide(rid, row.row_id, slot=1, reviewer="Dharma", decision="CONFIRM_DISCREPANCY", comment="qty wrong")
    assert store.row_state(rid, row.row_id).state == "REVIEWER_1_COMPLETE"
    store.decide(rid, row.row_id, slot=2, reviewer="Hemant", decision="ACCEPT", comment="label is right", blind=True)
    view = store.row_state(rid, row.row_id)
    assert view.state == "DISAGREEMENT"
    assert view.decisions[2].blind is True
    store.finalize(rid, row.row_id, final_decision="CONFIRM_DISCREPANCY", by="Dharma", note="agreed in cross-check meeting")
    view = store.row_state(rid, row.row_id)
    assert view.state == "FINALIZED" and view.final.final_decision == "CONFIRM_DISCREPANCY"
    history = store.history(rid, row.row_id)
    assert [h["event"] for h in history] == ["engine", "reviewer_1", "reviewer_2", "final"]


def test_agreement_state(ws_and_run, store):
    ws, run = ws_and_run
    rid = run.metadata.run_id
    row = _row(run, Classification.EXACT)
    store.decide(rid, row.row_id, slot=1, reviewer="Dharma", decision="ACCEPT")
    store.decide(rid, row.row_id, slot=2, reviewer="Hemant", decision="ACCEPT")
    assert store.row_state(rid, row.row_id).state == "AGREED"


def test_blind_view_hides_reviewer_one_until_reviewer_two_submits(ws_and_run, store):
    ws, run = ws_and_run
    rid = run.metadata.run_id
    row = _row(run, Classification.POTENTIAL)
    store.decide(rid, row.row_id, slot=1, reviewer="Dharma", decision="ACCEPT")
    hidden = store.rows_for_viewer(rid, [row], viewer_slot=2, blind=True)[0]
    # The row state is masked too: "REVIEWER_1_COMPLETE" would tell reviewer 2 that reviewer 1 had
    # already decided this row, which blind review is meant to withhold.
    assert hidden["decisions"].get(1) is None and hidden["state"] == "ENGINE_RECOMMENDED"
    assert hidden["engine"]["classification"] == "POTENTIAL"  # system recommendation stays visible
    store.decide(rid, row.row_id, slot=2, reviewer="Hemant", decision="ACCEPT", blind=True)
    shown = store.rows_for_viewer(rid, [row], viewer_slot=2, blind=True)[0]
    assert shown["decisions"][1]["decision"] == "ACCEPT"
    open_view = store.rows_for_viewer(rid, [row], viewer_slot=1, blind=False)[0]
    assert open_view["decisions"][2]["decision"] == "ACCEPT"


def test_bulk_accept_clean_rows(ws_and_run, store):
    ws, run = ws_and_run
    rid = run.metadata.run_id
    n = store.bulk_accept_clean(rid, run.results, slot=1, reviewer="Dharma")
    clean = [r for r in run.results if not r.requires_validation]
    assert n == len(clean) > 0
    assert store.row_state(rid, clean[0].row_id).decisions[1].decision == "ACCEPT"
    assert store.row_state(rid, _row(run, Classification.MISMATCH).row_id).state == "ENGINE_RECOMMENDED"


def test_summary_counts_by_state(ws_and_run, store):
    ws, run = ws_and_run
    rid = run.metadata.run_id
    store.decide(rid, _row(run, Classification.MISMATCH).row_id, slot=1, reviewer="Dharma", decision="CONFIRM_DISCREPANCY")
    counts = store.state_counts(rid, run.results)
    assert counts["ENGINE_RECOMMENDED"] == len(run.results) - 1 and counts["REVIEWER_1_COMPLETE"] == 1


def test_invalid_decision_rejected(ws_and_run, store):
    ws, run = ws_and_run
    with pytest.raises(ValueError):
        store.decide(run.metadata.run_id, "R-x", slot=1, reviewer="x", decision="MAYBE")
    with pytest.raises(ValueError):
        store.decide(run.metadata.run_id, "R-x", slot=3, reviewer="x", decision="ACCEPT")

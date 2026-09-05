"""Terminology worklist: which unconfirmed pairings, if approved as relationships, clear the most rows.

Turns the business-case projection ("after reviewers confirm the strong pairings") into a ranked to-do list
with the rows each approval would auto-clear and the cumulative effect.
"""

import pytest

from kaizen.datasets.build import build_golden
from kaizen.models import Thresholds
from kaizen.pipeline import run_folder
from kaizen.review.mining import approve_suggestion, terminology_worklist
from kaizen.review.store import ReviewStore
from kaizen.workspace import Workspace


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = tmp_path_factory.mktemp("worklist")
    golden = build_golden(root / "golden")
    ws = Workspace(root / "ws")
    run = run_folder(golden, ws.repository.store(), Thresholds())
    return golden, ws, run


def test_worklist_ranks_pairings_by_the_rows_they_would_clear(env):
    _, ws, run = env
    wl = terminology_worklist(run, ReviewStore(ws.db), ws.repository)
    assert wl.needs_validation > 0 and wl.items
    clears = [i.would_clear for i in wl.items]
    assert clears == sorted(clears, reverse=True), "worklist must be ordered by impact"
    assert wl.items[0].cumulative_clear == wl.items[0].would_clear
    assert wl.items[-1].cumulative_clear == sum(clears)
    assert 0 < wl.items[-1].cumulative_pct <= 100
    chlora = next(i for i in wl.items if "CHLORAPREP" in i.a_text.upper())
    assert chlora.would_clear >= 8, "one clean ChloraPrep pairing per SKU"
    assert chlora.sku_count == chlora.would_clear + chlora.still_review


def test_rows_with_a_discrepancy_still_need_review_after_confirmation(env):
    _, ws, run = env
    wl = terminology_worklist(run, ReviewStore(ws.db), ws.repository)
    # The terse "NEEDLE 21G" line fits two label lines equally well: that row is AMBIGUOUS and stays with a
    # reviewer even if the wording pairing is approved.
    needles = [i for i in wl.items if i.a_text.upper() == "NEEDLE 21G"]
    assert needles and any(i.still_review >= 1 for i in needles)
    assert all(i.would_clear + i.still_review == len(i.row_ids) for i in wl.items)


def test_top_n_summary_is_a_plain_sentence_worth_of_numbers(env):
    _, ws, run = env
    wl = terminology_worklist(run, ReviewStore(ws.db), ws.repository)
    top = wl.top(5)
    assert top["n"] == 5 and top["rows"] == sum(i.would_clear for i in wl.items[:5])
    assert top["pct"] == round(100 * top["rows"] / wl.needs_validation, 1)
    assert wl.top(0) == {"n": 0, "rows": 0, "pct": 0.0}
    d = wl.to_dict()
    assert d["needs_validation"] == wl.needs_validation and len(d["items"]) == len(wl.items)


def test_an_approved_pairing_leaves_the_worklist_on_the_next_run(env):
    golden, ws, run = env
    review = ReviewStore(ws.db)
    before = terminology_worklist(run, review, ws.repository)
    chlora = next(i for i in before.items if "CHLORAPREP" in i.a_text.upper())
    approve_suggestion(ws.repository, chlora, by="Dharma", scope="global")
    rerun = run_folder(golden, ws.repository.store(), Thresholds())
    after = terminology_worklist(rerun, review, ws.repository)
    assert not any("CHLORAPREP" in i.a_text.upper() for i in after.items)
    assert after.needs_validation <= before.needs_validation - chlora.would_clear

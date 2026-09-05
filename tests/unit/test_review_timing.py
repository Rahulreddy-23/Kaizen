"""Measured review effort: the time between a reviewer opening a row and deciding it.

The business case used to assume 1.5 minutes per row needing validation. With enough timed decisions the
assumption is replaced by the measured median, and the case says which one it used.
"""

import pytest

from kaizen.models import CheckResult, CheckType, Classification, MatchLevel, Thresholds
from kaizen.review.business import MIN_TIMED_SAMPLES, BusinessAssumptions, business_case
from kaizen.review.store import MAX_TIMED_SECONDS, ReviewStore, ReviewTiming
from kaizen.storage.db import Database


@pytest.fixture()
def store(tmp_path):
    return ReviewStore(Database(tmp_path / "kaizen.db"))


def _row(i: int) -> CheckResult:
    return CheckResult(row_id=f"R-{i}", sku="1295108NS", check=CheckType.BOM_LABEL, classification=Classification.EXACT, match_level=MatchLevel.EXACT, score=1.0, explanation="ok")


def test_decision_records_seconds_since_the_row_was_opened(store):
    store.mark_opened("run1", "R-1", slot=1, at="2026-09-05T10:00:00+00:00")
    d = store.decide("run1", "R-1", slot=1, reviewer="Dharma", decision="ACCEPT", now="2026-09-05T10:01:30+00:00")
    assert d.seconds_spent == 90
    assert store.decisions("run1", "R-1")[1].seconds_spent == 90


def test_decision_without_an_open_is_not_timed(store):
    d = store.decide("run1", "R-1", slot=1, reviewer="Dharma", decision="ACCEPT")
    assert d.seconds_spent is None


def test_each_slot_is_timed_separately(store):
    store.mark_opened("run1", "R-1", slot=1, at="2026-09-05T10:00:00+00:00")
    store.mark_opened("run1", "R-1", slot=2, at="2026-09-05T10:05:00+00:00")
    d2 = store.decide("run1", "R-1", slot=2, reviewer="Hemant", decision="ACCEPT", now="2026-09-05T10:05:20+00:00")
    assert d2.seconds_spent == 20


def test_implausibly_long_gaps_are_not_counted(store):
    """A row left open over lunch is not a measurement of review effort."""
    store.mark_opened("run1", "R-1", slot=1, at="2026-09-05T10:00:00+00:00")
    d = store.decide("run1", "R-1", slot=1, reviewer="Dharma", decision="ACCEPT", now="2026-09-05T11:00:00+00:00")
    assert d.seconds_spent is None and MAX_TIMED_SECONDS < 3600


def test_reopening_a_row_restarts_the_clock(store):
    store.mark_opened("run1", "R-1", slot=1, at="2026-09-05T10:00:00+00:00")
    store.mark_opened("run1", "R-1", slot=1, at="2026-09-05T10:10:00+00:00")
    d = store.decide("run1", "R-1", slot=1, reviewer="Dharma", decision="ACCEPT", now="2026-09-05T10:10:45+00:00")
    assert d.seconds_spent == 45


def test_bulk_accept_is_never_timed(store):
    rows = [_row(1), _row(2)]
    store.mark_opened("run1", "R-1", slot=1)
    assert store.bulk_accept_clean("run1", rows, slot=1, reviewer="Dharma") == 2
    assert all(d.seconds_spent is None for d in store.decisions("run1", "R-1").values())


def test_timing_summary_uses_only_timed_decisions(store):
    for i, secs in enumerate([30, 60, 90, 600], start=1):
        store.mark_opened("run1", f"R-{i}", slot=1, at="2026-09-05T10:00:00+00:00")
        store.decide("run1", f"R-{i}", slot=1, reviewer="Dharma", decision="ACCEPT", now=f"2026-09-05T10:{secs // 60:02d}:{secs % 60:02d}+00:00")
    store.decide("run1", "R-9", slot=1, reviewer="Dharma", decision="ACCEPT")  # untimed
    t = store.timing("run1")
    assert t.samples == 4 and t.median_seconds == 75 and t.mean_seconds == 195
    assert store.timing("other-run").samples == 0


def test_timing_can_be_restricted_to_rows_needing_validation(store):
    store.mark_opened("run1", "R-1", slot=1, at="2026-09-05T10:00:00+00:00")
    store.decide("run1", "R-1", slot=1, reviewer="Dharma", decision="ACCEPT", now="2026-09-05T10:00:20+00:00")
    store.mark_opened("run1", "R-2", slot=1, at="2026-09-05T10:00:00+00:00")
    store.decide("run1", "R-2", slot=1, reviewer="Dharma", decision="ACCEPT", now="2026-09-05T10:02:00+00:00")
    assert store.timing("run1", row_ids={"R-2"}).median_seconds == 120


# ---- business case -----------------------------------------------------------------------------


def _golden_run(tmp_path):
    from kaizen.datasets.build import build_golden
    from kaizen.pipeline import run_folder
    from kaizen.terminology.store import RelationshipStore

    return run_folder(build_golden(tmp_path / "golden"), RelationshipStore.default(), Thresholds())


def test_business_case_is_assumed_without_timing(tmp_path):
    bc = business_case(_golden_run(tmp_path))
    assert bc.effort_basis == "assumed" and bc.timed_decisions == 0
    assert bc.minutes_per_validation_row_used == BusinessAssumptions().minutes_per_validation_row
    assert any("assumed" in a.lower() for a in bc.assumptions)


def test_business_case_uses_the_measured_median_with_enough_samples(tmp_path):
    run = _golden_run(tmp_path)
    timing = ReviewTiming(samples=MIN_TIMED_SAMPLES, median_seconds=45.0, mean_seconds=50.0)
    bc = business_case(run, timing=timing)
    assert bc.effort_basis == "measured" and bc.timed_decisions == MIN_TIMED_SAMPLES
    assert bc.minutes_per_validation_row_used == 0.75 and bc.measured_minutes_per_validation_row == 0.75
    assumed = business_case(run)
    assert bc.estimated_minutes_per_sku < assumed.estimated_minutes_per_sku
    assert any("measured" in a.lower() and str(MIN_TIMED_SAMPLES) in a for a in bc.assumptions)


def test_too_few_timed_decisions_keep_the_assumption_but_are_reported(tmp_path):
    run = _golden_run(tmp_path)
    bc = business_case(run, timing=ReviewTiming(samples=MIN_TIMED_SAMPLES - 1, median_seconds=45.0, mean_seconds=50.0))
    assert bc.effort_basis == "assumed" and bc.timed_decisions == MIN_TIMED_SAMPLES - 1
    assert bc.measured_minutes_per_validation_row == 0.75
    assert bc.minutes_per_validation_row_used == BusinessAssumptions().minutes_per_validation_row

"""Relationship mining suggestions (human approval required) and the business-case calculator (measured, not assumed)."""

from kaizen.datasets.build import build_golden
from kaizen.models import Thresholds
from kaizen.pipeline import run_folder
from kaizen.review.business import BusinessAssumptions, business_case
from kaizen.review.mining import mine_suggestions
from kaizen.review.store import ReviewStore
from kaizen.workspace import Workspace


def test_mining_finds_repeated_potential_pairs_across_skus(tmp_path):
    golden = build_golden(tmp_path / "golden")
    ws = Workspace(tmp_path / "ws")
    run = run_folder(golden, ws.repository.store(), Thresholds())
    suggestions = mine_suggestions(run, ReviewStore(ws.db), ws.repository, min_skus=2)
    assert suggestions
    top = suggestions[0]
    assert top.sku_count >= 2 and top.a_text and top.b_text and top.check_types
    assert top.confirmed == 0 and top.contradicted == 0
    assert all(s.relationship_id is None for s in suggestions)  # not created automatically
    chlora = next(s for s in suggestions if "CHLORAPREP" in s.a_text.upper())
    assert chlora.sku_count >= 8 and "ChloraPrep" in chlora.b_text


def test_mining_counts_reviewer_confirmations_and_contradictions(tmp_path):
    golden = build_golden(tmp_path / "golden")
    ws = Workspace(tmp_path / "ws")
    run = run_folder(golden / "sku-001", ws.repository.store(), Thresholds())
    review = ReviewStore(ws.db)
    row = next(r for r in run.results if r.source_a and r.source_a.description == "CHLORAPREP APPLICATOR 3ML" and r.check.value == "BOM_LABEL")
    review.decide(run.metadata.run_id, row.row_id, slot=1, reviewer="Dharma", decision="ACCEPT")
    s = next(x for x in mine_suggestions(run, review, ws.repository, min_skus=1) if "CHLORAPREP" in x.a_text.upper() and "BOM_LABEL" in x.check_types)
    assert s.confirmed == 1 and s.contradicted == 0
    review.decide(run.metadata.run_id, row.row_id, slot=2, reviewer="Hemant", decision="CONFIRM_DISCREPANCY")
    s = next(x for x in mine_suggestions(run, review, ws.repository, min_skus=1) if "CHLORAPREP" in x.a_text.upper() and "BOM_LABEL" in x.check_types)
    assert s.confirmed == 1 and s.contradicted == 1


def test_mining_excludes_pairs_already_covered_by_relationships(tmp_path):
    golden = build_golden(tmp_path / "golden")
    ws = Workspace(tmp_path / "ws")
    run_folder(golden / "sku-001", ws.repository.store(), Thresholds())
    ws.repository.create(canonical="ChloraPrep™ Solution One-Step Applicator, 3 mL", aliases=["CHLORAPREP APPLICATOR 3ML"], created_by="t")
    run2 = run_folder(golden / "sku-001", ws.repository.store(), Thresholds())
    assert not any("CHLORAPREP" in s.a_text.upper() for s in mine_suggestions(run2, ReviewStore(ws.db), ws.repository, min_skus=1))


def test_business_case_uses_actual_run_metrics_and_shows_assumptions(tmp_path):
    golden = build_golden(tmp_path / "golden")
    ws = Workspace(tmp_path / "ws")
    run = run_folder(golden, ws.repository.store(), Thresholds())
    from kaizen.review.business import reviewable

    bc = business_case(run, BusinessAssumptions())
    assert bc.skus == 10 and bc.rows == len(reviewable(run)) < len(run.results)
    assert bc.auto_cleared + bc.needs_validation == bc.rows
    assert bc.baseline_minutes_per_sku == 60 and bc.hourly_rate == 37.5 and bc.skus_per_project == 100 and bc.projects_per_year == 20
    assert bc.estimated_minutes_per_sku > 0
    assert abs(bc.minutes_saved_per_sku - (60 - bc.estimated_minutes_per_sku)) < 1e-9
    assert bc.reduction_pct == round(100 * bc.minutes_saved_per_sku / 60, 1)
    assert bc.hours_saved_per_project == round(bc.minutes_saved_per_sku * 100 * 2 / 60, 1)
    assert bc.annual_savings == round(bc.hours_saved_per_project * 37.5 * 20, 2)
    assert "minutes per row needing validation" in " ".join(bc.assumptions).lower()
    assert isinstance(bc.meets_target, bool)


def test_business_case_is_honest_when_everything_needs_review(tmp_path):
    golden = build_golden(tmp_path / "golden")
    ws = Workspace(tmp_path / "ws")
    run = run_folder(golden / "sku-001", ws.repository.store(), Thresholds())
    slow = BusinessAssumptions(minutes_per_validation_row=10.0, minutes_per_cleared_row=1.0)
    bc = business_case(run, slow)
    assert bc.minutes_saved_per_sku < 0 and bc.meets_target is False


def test_business_case_shows_measured_and_projected_after_confirmation(tmp_path):
    golden = build_golden(tmp_path / "golden")
    ws = Workspace(tmp_path / "ws")
    run = run_folder(golden, ws.repository.store(), Thresholds())
    bc = business_case(run, BusinessAssumptions())
    # measured with defaults: most validations are strong fuzzy pairings the engine refuses to auto-clear
    assert bc.confirmable_rows > 100 and bc.confirmable_rows <= bc.needs_validation
    assert bc.needs_validation_after_confirmation == bc.needs_validation - bc.confirmable_rows
    assert bc.reduction_pct_after_confirmation > bc.reduction_pct
    assert any("projection" in a.lower() for a in bc.assumptions)
    assert bc.meets_target is False and isinstance(bc.meets_target_after_confirmation, bool)

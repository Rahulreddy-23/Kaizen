"""Measured accuracy on the committed golden dataset. Floors are asserted, never assumed."""

from pathlib import Path

import pytest

from kaizen.evaluation.ground_truth import load_ground_truth
from kaizen.evaluation.harness import evaluate
from kaizen.models import Thresholds
from kaizen.pipeline import run_folder
from kaizen.terminology.store import RelationshipStore

GOLDEN = Path(__file__).resolve().parents[2] / "datasets" / "golden"


@pytest.fixture(scope="module")
def metrics():
    assert (GOLDEN / "ground-truth.json").exists(), "run `kaizen dataset build` first"
    run = run_folder(GOLDEN, RelationshipStore.default(), Thresholds())
    return evaluate(run, load_ground_truth(GOLDEN / "ground-truth.json"))


def test_discrepancy_precision_and_recall_floor(metrics):
    assert metrics.overall.precision >= 0.95, metrics.mismatches
    assert metrics.overall.recall >= 0.95, metrics.mismatches


def test_no_false_missing_from_non_physical_or_inactive_rows(metrics):
    assert metrics.false_missing == 0, metrics.mismatches


def test_pairing_and_classification_floors(metrics):
    assert metrics.pairing_accuracy >= 0.95, metrics.mismatches
    assert metrics.classification_accuracy >= 0.95, metrics.mismatches
    assert metrics.ref_check_accuracy == 1.0, metrics.mismatches


def test_every_sku_produced_results(metrics):
    assert metrics.missing_skus == []


def test_pco_bom_check_is_measured_and_correct(metrics):
    pco = metrics.per_check["PCO_BOM"]
    assert pco.scored_rows >= 20
    assert pco.counts.precision >= 0.95 and pco.counts.recall >= 0.95, metrics.mismatches
    assert pco.classification_accuracy >= 0.95, metrics.mismatches
    assert metrics.per_type["PCO_CHANGE_NOT_APPLIED"].tp >= 2
    assert metrics.per_type["PCO_QTY_SEQ_MISMATCH"].tp >= 1


def test_coverage_blocker_for_missing_bom_is_detected(metrics):
    cov = metrics.per_check["COVERAGE"]
    assert cov.counts.tp == 1 and cov.counts.fp == 0 and cov.counts.fn == 0, metrics.mismatches


def test_drawing_checks_are_measured_and_correct(metrics):
    for name in ("BOM_DRAWING", "LABEL_DRAWING"):
        cm = metrics.per_check[name]
        assert cm.scored_rows >= 300, name
        assert cm.counts.precision >= 0.95 and cm.counts.recall >= 0.95, (name, metrics.mismatches)
        assert cm.classification_accuracy >= 0.95, (name, metrics.mismatches)
    assert metrics.per_type["MISSING_IN_DRAWING"].tp >= 3
    assert metrics.per_type["EXTRA_ON_DRAWING"].tp >= 1


def test_label_revision_check_is_measured_and_correct(metrics):
    cm = metrics.per_check["LABEL_REVISION"]
    assert cm.scored_rows >= 12
    assert cm.counts.precision >= 0.95 and cm.counts.recall >= 0.95, metrics.mismatches
    assert cm.classification_accuracy >= 0.95, metrics.mismatches
    assert metrics.per_type["EXPECTED_CHANGE_ABSENT"].tp >= 2
    assert metrics.per_type["UNEXPECTED_LABEL_CHANGE"].tp >= 2

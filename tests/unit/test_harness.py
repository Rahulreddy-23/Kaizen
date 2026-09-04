import json

import pytest

from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.evaluation.ground_truth import load_ground_truth
from kaizen.evaluation.harness import evaluate
from kaizen.models import Thresholds
from kaizen.pipeline import run_folder
from kaizen.terminology.store import RelationshipStore


def make_dataset(tmp_path, gt_overrides=None):
    render_bom_pdf(
        BomSpec(
            parent_item="1295108NS",
            parent_description="KIT A",
            rows=[
                BomRowSpec(item="0396447", description="ABSORBENT TOWEL"),
                BomRowSpec(item="5167473", description="TAPE ANCHOR PER-Q-CATH", qty_per="2.0000"),
                BomRowSpec(item="8880001", description="LONELY PART"),
                BomRowSpec(item="BAW0724416", description="EN LOD, UNIT LABEL"),
            ],
        ),
        tmp_path / "sku-001" / "bom.pdf",
    )
    render_label_pdf(LabelSpec(ref="1295108", product_name="Kit A", contents=["1 Each - Towel, Absorbent", "1 Each - Surgical Tape", "1 Each - Mystery Widget"]), tmp_path / "sku-001" / "label.pdf")
    gt = {
        "version": 1,
        "skus": {
            "1295108NS": {
                "folder": "sku-001",
                "ref_check": "EXACT",
                "expected": [
                    {"bom_item": "0396447", "label": "Towel, Absorbent", "classification": "EXACT", "discrepancies": [], "scenario": "exact"},
                    {"bom_item": "5167473", "label": "Surgical Tape", "classification": "MISMATCH", "discrepancies": ["QTY_MISMATCH"], "scenario": "qty-mismatch"},
                    {"bom_item": "8880001", "label": None, "classification": "MISSING", "discrepancies": ["MISSING_IN_LABEL"], "scenario": "missing-on-label"},
                    {"bom_item": None, "label": "Mystery Widget", "classification": "MISSING", "discrepancies": ["MISSING_IN_BOM"], "scenario": "extra-label-item"},
                ],
                "not_compared": ["BAW0724416"],
            }
        },
    }
    if gt_overrides:
        gt_overrides(gt)
    (tmp_path / "ground-truth.json").write_text(json.dumps(gt))
    return tmp_path


def test_perfect_agreement_scores_one(tmp_path):
    root = make_dataset(tmp_path)
    run = run_folder(root, RelationshipStore.default(), Thresholds())
    m = evaluate(run, load_ground_truth(root / "ground-truth.json"))
    assert m.overall.precision == 1.0 and m.overall.recall == 1.0
    assert m.overall.tp == 3 and m.overall.fp == 0 and m.overall.fn == 0
    assert m.classification_accuracy == 1.0
    assert m.pairing_accuracy == 1.0
    assert m.false_missing == 0
    assert m.ref_check_accuracy == 1.0
    assert set(m.per_type) >= {"QTY_MISMATCH", "MISSING_IN_LABEL", "MISSING_IN_BOM"}
    assert m.per_sku["1295108NS"].expected_rows == 4
    assert m.counts["EXACT"] >= 1 and m.counts["MISMATCH"] == 1
    d = m.to_dict()
    json.dumps(d)
    assert d["overall"]["precision"] == 1.0


def test_disagreement_is_counted_not_hidden(tmp_path):
    def tweak(gt):
        rows = gt["skus"]["1295108NS"]["expected"]
        rows[1]["classification"] = "EQUIVALENT"  # GT claims no qty problem → engine's QTY_MISMATCH becomes a false positive
        rows[1]["discrepancies"] = []
        rows[0]["discrepancies"] = ["DESC_MISMATCH"]  # GT expects something the engine does not report → false negative
        gt["skus"]["1295108NS"]["not_compared"].append("0396447")  # engine compares it → false-missing violation

    root = make_dataset(tmp_path, tweak)
    run = run_folder(root, RelationshipStore.default(), Thresholds())
    m = evaluate(run, load_ground_truth(root / "ground-truth.json"))
    assert m.overall.fp == 1 and m.overall.fn == 1
    assert m.overall.precision < 1.0 and m.overall.recall < 1.0
    assert m.classification_accuracy < 1.0
    assert m.false_missing == 1
    assert m.per_type["DESC_MISMATCH"].fn == 1
    assert m.mismatches  # human-readable list of disagreements
    assert any("5167473" in x for x in m.mismatches)


def test_wrong_pairing_is_detected(tmp_path):
    def tweak(gt):
        gt["skus"]["1295108NS"]["expected"][0]["label"] = "Surgical Tape"

    root = make_dataset(tmp_path, tweak)
    run = run_folder(root, RelationshipStore.default(), Thresholds())
    m = evaluate(run, load_ground_truth(root / "ground-truth.json"))
    assert m.pairing_accuracy < 1.0


def test_label_any_of_accepts_alternatives(tmp_path):
    def tweak(gt):
        row = gt["skus"]["1295108NS"]["expected"][0]
        row.pop("label")
        row["label_any_of"] = ["Towel, Absorbent", "Absorbent Towel"]

    root = make_dataset(tmp_path, tweak)
    run = run_folder(root, RelationshipStore.default(), Thresholds())
    m = evaluate(run, load_ground_truth(root / "ground-truth.json"))
    assert m.pairing_accuracy == 1.0


def test_ground_truth_validation_rejects_unknown_classification(tmp_path):
    bad = {"version": 1, "skus": {"X": {"folder": "x", "expected": [{"bom_item": "1", "label": None, "classification": "MAYBE", "discrepancies": []}]}}}
    (tmp_path / "gt.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError):
        load_ground_truth(tmp_path / "gt.json")


def test_sku_in_ground_truth_but_not_in_run_is_reported(tmp_path):
    def tweak(gt):
        gt["skus"]["9999999NS"] = {"folder": "sku-009", "expected": [{"bom_item": "1", "label": None, "classification": "MISSING", "discrepancies": ["MISSING_IN_LABEL"]}]}

    root = make_dataset(tmp_path, tweak)
    run = run_folder(root, RelationshipStore.default(), Thresholds())
    m = evaluate(run, load_ground_truth(root / "ground-truth.json"))
    assert "9999999NS" in m.missing_skus
    assert m.overall.fn >= 1

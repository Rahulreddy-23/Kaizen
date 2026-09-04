import hashlib
import json

from kaizen.datasets.build import REQUIRED_SCENARIOS, build_golden
from kaizen.datasets.scenarios import SCENARIOS


def _hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def test_build_creates_ten_skus_with_documents_and_ground_truth(tmp_path):
    root = build_golden(tmp_path / "golden")
    skus = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("sku-"))
    assert len(skus) == 10
    for sku_dir in skus:
        names = {p.name for p in sku_dir.iterdir()}
        assert "label.pdf" in names and "drawing.pdf" in names
        assert names & {"bom.pdf", "bom.xlsx", "bom.csv"}
    gt = json.loads((root / "ground-truth.json").read_text())
    assert gt["version"] == 1 and len(gt["skus"]) == 10
    assert (root / "SCENARIOS.md").exists()
    assert all(s["expected"] for s in gt["skus"].values())


def test_scenarios_cover_all_required_cases(tmp_path):
    root = build_golden(tmp_path / "golden")
    gt = json.loads((root / "ground-truth.json").read_text())
    tags = {row.get("scenario") for s in gt["skus"].values() for row in s["expected"]}
    tags |= {t for s in SCENARIOS for t in s.tags}
    missing = set(REQUIRED_SCENARIOS) - tags
    assert not missing, f"scenarios not covered: {missing}"


def test_build_is_deterministic(tmp_path):
    first = _hashes(build_golden(tmp_path / "a"))
    second = _hashes(build_golden(tmp_path / "b"))
    assert first == second


def test_ground_truth_matches_scenario_definitions(tmp_path):
    root = build_golden(tmp_path / "golden")
    gt = json.loads((root / "ground-truth.json").read_text())
    for scenario in SCENARIOS:
        entry = gt["skus"][scenario.parent_item]
        assert entry["folder"] == scenario.folder
        assert len(entry["expected"]) == len([l for l in scenario.lines if l.expected is not None])


def test_build_includes_pcos_and_pco_ground_truth(tmp_path):
    root = build_golden(tmp_path / "golden")
    assert (root / "pco" / "PCO34590.xlsx").exists() and (root / "pco" / "PCO34591.pdf").exists()
    gt = json.loads((root / "ground-truth.json").read_text())
    assert gt["coverage"]["missing_boms"] == [{"pco": "PCO34590", "code": "1495108NS"}]
    assert gt["skus"]["1395108QNS"]["pco_bom"][0] == {"change_key": "DELETE:RM5002565", "classification": "MISMATCH", "discrepancies": ["PCO_CHANGE_NOT_APPLIED"], "scenario": "pco-delete-not-applied"}
    assert any(r["change_key"] == "SUBSTITUTE:2370001>2370002" for r in gt["skus"]["2131910FNS"]["pco_bom"])


def test_ground_truth_has_drawing_rows_and_rev_mismatch(tmp_path):
    root = build_golden(tmp_path / "golden")
    gt = json.loads((root / "ground-truth.json").read_text())
    assert gt["skus"]["1275108NS"]["drawing_ref"] == "DRAWING_REV_MISMATCH"
    assert len(gt["skus"]["1295108NS"]["bom_drawing"]) >= 30 and len(gt["skus"]["1295108NS"]["label_drawing"]) >= 30
    assert any(r["discrepancies"] == ["EXTRA_ON_DRAWING"] for r in gt["skus"]["2131910NS"]["bom_drawing"])

"""A "corrected copy" of one SKU set: the same scenario re-rendered with its seeded discrepancies removed.
The demo's corrected-rerun beat needs it, and so does anyone rehearsing verify-and-close."""

from kaizen.datasets.build import build_corrected, build_golden
from kaizen.models import Thresholds
from kaizen.pipeline import run_folder
from kaizen.review.rundiff import diff_runs
from kaizen.terminology.store import RelationshipStore


def test_corrected_copy_of_a_sku_has_no_item_discrepancies_and_diffs_as_resolved(tmp_path):
    golden = build_golden(tmp_path / "golden")
    corrected = build_corrected(tmp_path / "corrected", "1295108FNS")
    assert (corrected / "sku-002" / "bom.pdf").exists() and (corrected / "sku-002" / "label.pdf").exists()
    assert not (corrected / "pco").exists(), "the corrected copy is the fixed SKU set alone"
    store = RelationshipStore.default()
    before = run_folder(golden, store, Thresholds())
    after = run_folder(corrected, store, Thresholds())
    rows = [r for r in after.results if r.sku == "1295108FNS" and r.role == "item" and r.check.value == "BOM_LABEL"]
    assert rows and all(not r.discrepancies for r in rows)
    d = diff_runs(before, after)
    resolved = [c for c in d.rows if c.status == "resolved" and c.sku == "1295108FNS"]
    assert len(resolved) >= 2, "the gauze and end-cap quantity mismatches are gone"
    assert d.counts["new"] == 0


def test_unknown_sku_is_refused(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        build_corrected(tmp_path / "x", "0000000XX")

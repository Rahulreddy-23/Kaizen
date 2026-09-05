"""Run-to-run diff: after corrected documents come back, show only what changed — resolved, new, still open."""

import json

from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.models import Thresholds
from kaizen.pipeline import run_folder
from kaizen.review.rundiff import diff_runs
from kaizen.terminology.store import RelationshipStore


def _dataset(root, end_cap_qty="2.0000", towel=True):
    rows = [BomRowSpec(item="2260001", description="END CAP", qty_per=end_cap_qty)]
    if towel:
        rows.insert(0, BomRowSpec(item="0396447", description="ABSORBENT TOWEL"))
    render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=rows), root / "sku-001" / "bom.pdf")
    render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - Towel, Absorbent", "1 Each - End Cap"]), root / "sku-001" / "label.pdf")
    return root


def _run(root):
    return run_folder(root, RelationshipStore.default(), Thresholds())


def test_corrected_mismatch_is_resolved_and_everything_else_unchanged(tmp_path):
    before = _run(_dataset(tmp_path / "a"))
    after = _run(_dataset(tmp_path / "b", end_cap_qty="1.0000"))
    d = diff_runs(before, after)
    assert d.counts["resolved"] == 1 and d.counts["new"] == 0 and d.counts["still_open"] == 0
    assert d.counts["unchanged"] > 0
    r = next(c for c in d.rows if c.status == "resolved")
    assert "2260001" in r.key and r.before["discrepancies"] == ["QTY_MISMATCH"] and r.after["discrepancies"] == []
    assert r.before["row_id"] and r.after["row_id"]
    assert all(c.status != "unchanged" for c in d.rows), "unchanged rows are counted, not listed"
    assert d.skus == {"added": [], "removed": [], "common": ["1295108NS"]}
    changed = [c["path"] for c in d.documents["changed"]]
    assert changed == ["sku-001/bom.pdf"], "only the BOM was corrected"
    assert d.documents["added"] == [] and d.documents["removed"] == []


def test_a_regression_shows_as_new_and_an_uncorrected_one_as_still_open(tmp_path):
    good = _run(_dataset(tmp_path / "a", end_cap_qty="1.0000"))
    bad = _run(_dataset(tmp_path / "b"))
    d = diff_runs(good, bad)
    assert d.counts["new"] == 1 and d.counts["resolved"] == 0
    same = diff_runs(bad, _run(_dataset(tmp_path / "c")))
    assert same.counts["still_open"] == 1 and same.counts["new"] == 0 and same.counts["resolved"] == 0


def test_a_row_that_disappears_with_its_document_line_is_reported_not_silently_resolved(tmp_path):
    before = _run(_dataset(tmp_path / "a"))
    after = _run(_dataset(tmp_path / "b", towel=False))  # towel removed from the BOM: label now has an extra line
    d = diff_runs(before, after)
    statuses = {c.key: c.status for c in d.rows}
    assert any(k.endswith("A:0396447") and s == "gone" for k, s in statuses.items()), "the towel comparison no longer exists"
    assert d.counts["new"] >= 1, "the label line without a BOM item is a new discrepancy"


def test_skus_present_in_only_one_run_are_listed_not_diffed(tmp_path):
    before = _run(_dataset(tmp_path / "a"))
    other = tmp_path / "other"
    render_bom_pdf(BomSpec(parent_item="7770001NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), other / "sku-x" / "bom.pdf")
    render_label_pdf(LabelSpec(ref="7770001", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), other / "sku-x" / "label.pdf")
    d = diff_runs(before, _run(other))
    assert d.skus["removed"] == ["1295108NS"] and d.skus["added"] == ["7770001NS"] and d.skus["common"] == []
    assert d.counts["not_covered"] >= 2 and d.rows == [], "rows of a SKU present in only one run are counted, not diffed"


def test_diff_is_json_serialisable(tmp_path):
    d = diff_runs(_run(_dataset(tmp_path / "a")), _run(_dataset(tmp_path / "b", end_cap_qty="1.0000")))
    payload = json.loads(json.dumps(d.to_dict()))
    assert payload["before_run_id"] and payload["after_run_id"] and payload["counts"]["resolved"] == 1

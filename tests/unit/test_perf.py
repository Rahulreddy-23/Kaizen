"""Performance harness: synthetic N-SKU datasets, timed phases. Small N here; `kaizen perf --skus 100` for the real thing."""

from kaizen.perf import build_perf_dataset, measure


def test_perf_harness_builds_and_measures(tmp_path):
    root = build_perf_dataset(tmp_path / "perf", skus=3)
    assert sum(1 for p in root.iterdir() if p.is_dir() and p.name.startswith("sku-")) == 3
    m = measure(root)
    assert m.skus == 3 and m.rows > 200 and m.documents == 9
    assert m.ingest_seconds > 0 and m.matching_seconds > 0 and m.report_seconds > 0
    assert abs(m.total_seconds - (m.ingest_seconds + m.matching_seconds + m.report_seconds)) < 0.05
    assert m.peak_memory_mb is None or m.peak_memory_mb > 0
    d = m.to_dict()
    assert d["rows_per_second"] > 0

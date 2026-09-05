"""Cross-check certificate: one page per SKU that mirrors today's "checked by + date" stamp, with the
evidence that makes it verifiable — run id, file hashes, counts, both reviewers and open action items."""

import pymupdf
import pytest

from kaizen.datasets.build import build_golden
from kaizen.models import Thresholds
from kaizen.pipeline import run_folder
from kaizen.reporting.certificate import write_certificate, write_run_certificate
from kaizen.reporting.excel import ReviewBundle
from kaizen.review.action_items import ActionItemStore
from kaizen.review.store import ReviewStore
from kaizen.workspace import Workspace


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = tmp_path_factory.mktemp("cert")
    golden = build_golden(root / "golden")
    ws = Workspace(root / "ws")
    run = run_folder(golden, ws.repository.store(), Thresholds())
    review = ReviewStore(ws.db)
    rid = run.metadata.run_id
    rows = [r for r in run.results if r.sku == "1295108FNS" and r.role == "item"]
    mismatch = next(r for r in rows if r.classification.value == "MISMATCH")
    review.decide(rid, mismatch.row_id, 1, "Dharma Reddy", "CONFIRM_DISCREPANCY", comment="qty wrong")
    review.decide(rid, mismatch.row_id, 2, "Hemant Rao", "CONFIRM_DISCREPANCY", comment="agree", blind=True)
    review.finalize(rid, mismatch.row_id, "CONFIRM_DISCREPANCY", by="Dharma Reddy", note="cross-check meeting")
    items = ActionItemStore(ws.db)
    ai = items.create_from_result(run, mismatch, reviewer="Dharma Reddy", owner="R&D")
    decisions = review.all_decisions(rid)
    bundle = ReviewBundle(decisions=decisions, finals=review.finals(rid), states={r.row_id: ReviewStore.state_of(decisions.get(r.row_id, {}), review.finals(rid).get(r.row_id)) for r in run.results}, action_items=items.for_run(rid))
    return root, run, bundle, ai


def _text(path) -> str:
    pdf = pymupdf.open(path)
    try:
        return "\n".join(p.get_text() for p in pdf)
    finally:
        pdf.close()


def test_certificate_is_one_page_with_identity_hashes_counts_and_reviewers(env):
    root, run, bundle, ai = env
    out = write_certificate(run, "1295108FNS", root / "cert.pdf", review=bundle)
    pdf = pymupdf.open(out)
    assert len(pdf) == 1
    pdf.close()
    text = _text(out)
    assert "1295108FNS" in text and run.metadata.run_id in text and run.metadata.tool_version in text
    group = next(g for g in run.groups if g.sku == "1295108FNS")
    for d in run.documents:
        if d.id in group.document_ids:
            assert d.sha256 in text, f"hash of {d.path} must be on the certificate"
    assert "Dharma Reddy" in text and "Hemant Rao" in text
    assert "MISMATCH" in text and "EXACT" in text and "validation" in text.lower()
    assert ai.id in text, "open action items are listed"
    assert "recommendation" in text.lower() and "decide" in text.lower()
    assert run.metadata.terminology_version[:16] in text


def test_certificate_without_reviews_says_so(env):
    root, run, _, _ = env
    text = _text(write_certificate(run, "1295108NS", root / "cert-none.pdf"))
    assert "1295108NS" in text
    assert "no reviewer decisions" in text.lower()


def test_run_certificate_has_one_page_per_sku_in_order(env):
    root, run, bundle, _ = env
    out = write_run_certificate(run, root / "cert-run.pdf", review=bundle)
    pdf = pymupdf.open(out)
    try:
        assert len(pdf) == len(run.groups)
        first = pdf[0].get_text()
        assert run.groups[0].sku in first
    finally:
        pdf.close()


def test_unknown_sku_is_refused(env):
    root, run, _, _ = env
    with pytest.raises(ValueError):
        write_certificate(run, "0000000XX", root / "nope.pdf")

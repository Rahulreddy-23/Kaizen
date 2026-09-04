"""Marked-up BOM PDF: coloured marks per check in the margin, never over the original text; honest fallback."""

import pymupdf
import pytest

from kaizen.datasets.build import build_golden
from kaizen.models import DocType, Thresholds
from kaizen.pipeline import run_folder
from kaizen.reporting.annotated_bom import write_annotated_bom
from kaizen.terminology.store import RelationshipStore


@pytest.fixture(scope="module")
def golden_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("g")
    golden = build_golden(root / "golden")
    return golden, run_folder(golden, RelationshipStore.default(), Thresholds())


def test_marks_are_drawn_in_margin_and_original_text_survives(golden_run, tmp_path):
    golden, run = golden_run
    bom = next(d for d in run.documents if d.doc_type is DocType.BOM and d.sku == "1295108FNS")
    before = [pymupdf.open(bom.path)[i].get_text() for i in range(len(pymupdf.open(bom.path)))]
    outcome = write_annotated_bom(run, bom, tmp_path / "bom_annotated.pdf", checked_by=["Dharma A", "Hemant Gudihal"])
    assert outcome.fallback is False and outcome.marks >= 30
    doc = pymupdf.open(outcome.path)
    for i, text in enumerate(before):
        assert all(line in doc[i].get_text() for line in text.splitlines() if line.strip())
    page1 = doc[0].get_text()
    assert "Compared with Label" in page1 and "Compared with PKG Drawings" in page1 and "Compared with PCO" in page1
    assert "Checked by" in page1 and "Dharma A" in page1 and run.metadata.run_id in page1
    drawings = [d for i in range(len(doc)) for d in doc[i].get_drawings()]
    assert len(drawings) >= outcome.marks
    original = pymupdf.open(bom.path)
    for i in range(len(doc)):
        max_x1 = max(w[2] for w in original[i].get_text("words"))
        marks_x = [d["rect"].x0 for d in doc[i].get_drawings() if d["rect"].width < 12 and d["rect"].y0 > 160]
        assert all(x >= max_x1 - 1 for x in marks_x)  # marks sit to the right of the printed text, never over it


def test_status_marks_follow_classification(golden_run, tmp_path):
    golden, run = golden_run
    bom = next(d for d in run.documents if d.doc_type is DocType.BOM and d.sku == "1295108FNS")
    outcome = write_annotated_bom(run, bom, tmp_path / "b.pdf")
    kinds = {m.kind for m in outcome.mark_list}
    assert kinds >= {"clear", "discrepancy", "review"}
    assert any(m.check == "BOM_LABEL" and m.kind == "discrepancy" and m.item == "2260001" for m in outcome.mark_list)
    assert any(m.check == "PCO_BOM" for m in outcome.mark_list)


def test_table_bom_falls_back_to_review_page(golden_run, tmp_path):
    golden, run = golden_run
    bom = next(d for d in run.documents if d.doc_type is DocType.BOM and d.sku == "2131910FNS")  # xlsx
    outcome = write_annotated_bom(run, bom, tmp_path / "b.pdf")
    assert outcome.fallback is True
    text = pymupdf.open(outcome.path)[0].get_text()
    assert "no page geometry" in text.lower() and "2131910FNS" in text and "END CAP" in text

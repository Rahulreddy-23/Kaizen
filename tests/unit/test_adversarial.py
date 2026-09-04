"""Adversarial cases beyond the golden set. Each one documents a real-world nuisance the engine must survive."""

from decimal import Decimal

import pymupdf

from kaizen.checks.bom_label import run_bom_label_check
from kaizen.ingest.pdf_words import extract_words, group_lines, line_text
from kaizen.matching.ladder import MatchLadder
from kaizen.models import Classification, DiscrepancyType, Severity, Thresholds
from kaizen.terminology.store import RelationshipStore
from tests.unit.test_bom_label_check import bom_doc, label_doc

TH = Thresholds()


def run(bom, label):
    return run_bom_label_check(bom, label, MatchLadder(RelationshipStore.default(), TH), TH)


def test_duplicate_bom_lines_for_same_item_are_merged_before_comparison():
    # JDE can list the same component twice (different operation sequences); the label shows the total.
    bom = bom_doc([("2260001", "END CAP", "1"), ("2260001", "END CAP", "1"), ("0396447", "ABSORBENT TOWEL", "1")])
    results = run(bom, label_doc([("End Cap", "2"), ("Towel, Absorbent", "1")]))
    caps = [r for r in results if r.source_a is not None and r.source_a.item_number == "2260001"]
    assert len(caps) == 1
    assert caps[0].classification is Classification.EXACT
    assert caps[0].source_a.quantity == Decimal("2")
    assert "merged" in caps[0].explanation.lower()
    assert caps[0].source_a.attributes["merged_rows"] == 2
    assert not any(d.type is DiscrepancyType.MISSING_IN_LABEL for r in results for d in r.discrepancies)


def test_label_with_no_extracted_contents_yields_one_blocker_not_many_missing_rows():
    bom = bom_doc([("0396447", "ABSORBENT TOWEL", "1"), ("2260001", "END CAP", "2"), ("2330001", "TOURNIQUET", "1")])
    results = run(bom, label_doc([]))
    item_rows = [r for r in results if not (r.source_a is not None and r.source_a.attributes.get("kind") == "header")]
    assert len(item_rows) == 1
    blocker = item_rows[0]
    assert blocker.classification is Classification.MISSING
    assert blocker.discrepancies[0].type is DiscrepancyType.LOW_EXTRACTION_CONFIDENCE
    assert blocker.discrepancies[0].severity is Severity.BLOCKER
    assert "3" in blocker.explanation  # tells the reviewer how many components were not individually listed
    assert blocker.requires_validation is True


def test_group_lines_tolerates_subpixel_vertical_jitter(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=200)
    page.insert_text((20, 50.0), "0396447", fontsize=8)
    page.insert_text((120, 51.4), "ABSORBENT TOWEL", fontsize=8)  # real PDFs jitter baselines by a point or two
    page.insert_text((300, 49.2), "1.0000", fontsize=8)
    page.insert_text((20, 62.0), "5167473", fontsize=8)  # next row only 12pt below
    path = tmp_path / "jitter.pdf"
    doc.save(path)
    lines = group_lines(extract_words(pymupdf.open(path)[0]))
    assert [line_text(l) for l in lines] == ["0396447 ABSORBENT TOWEL 1.0000", "5167473"]


def test_description_with_slash_and_ampersand_still_matches():
    bom = bom_doc([("2280001", "ECG LEADS & ELECTRODES ASSY", "1")])
    results = run(bom, label_doc([("ECG Leads/Electrodes Assembly", "1")]))
    r = [x for x in results if x.source_a is not None and x.source_a.item_number == "2280001"][0]
    assert r.classification is Classification.EXACT

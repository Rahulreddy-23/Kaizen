"""Regression tests for the findings of the forensic audit (docs/implementation-plan.md §13)."""

import threading
from decimal import Decimal

import pytest

from kaizen.checks.bom_label import run_bom_label_check
from kaizen.checks.label_revision import ExpectedChange, expected_changes_from_pcos, run_label_revision_check
from kaizen.checks.pco_bom import run_pco_bom_check
from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.ingest.bom_categorize import categorize
from kaizen.ingest.bom_pdf import parse_bom_pdf
from kaizen.ingest.quantity import parse_label_line
from kaizen.matching.fuzzy import similarity
from kaizen.matching.ladder import MatchLadder
from kaizen.matching.normalize import normalize
from kaizen.models import Classification, DiscrepancyType, ItemCategory, Relationship, SubQuantity, Thresholds
from kaizen.pipeline import run_folder
from kaizen.review.business import business_case
from kaizen.review.store import ReviewStore
from kaizen.terminology.store import RelationshipStore
from kaizen.workspace import Workspace
from tests.unit.test_bom_label_check import bom_doc, label_doc
from tests.unit.test_pco_bom_check import pco_doc

TH = Thresholds()
LADDER = MatchLadder(RelationshipStore.default(), TH)


# 1. Old ↔ New: sub-quantity and UOM changes must be visible
def test_revision_detects_sub_quantity_and_uom_changes():
    old = label_doc([("Tape Strips", "2", SubQuantity(value=3, kind="per", raw="(3 per)")), ("Gloves", "1")])
    new = label_doc([("Tape Strips", "2", SubQuantity(value=2, kind="per", raw="(2 per)")), ("Gloves", "1")])
    new.items[1].uom = "PAIR"
    results = run_label_revision_check(old, new, [], LADDER, TH, sku="1295108NS")
    changed = [r for r in results if r.discrepancies]
    assert len(changed) == 2
    assert all(d.type is DiscrepancyType.UNEXPECTED_LABEL_CHANGE for r in changed for d in r.discrepancies)
    assert any("SUB-QUANTITY CHANGED" in r.explanation and "(3 per)" in r.explanation and "(2 per)" in r.explanation for r in changed)
    assert any("UOM CHANGED" in r.explanation and "PAIR" in r.explanation for r in changed)


# 2. Fuzzy resemblance must not satisfy a PCO expectation
def test_fuzzy_fit_of_expected_change_is_potential_not_exact():
    old = label_doc([("Towel, Absorbent", "1")])
    new = label_doc([("Towel, Absorbent", "1"), ("Needle 22G x 1in", "1")])
    expected = [ExpectedChange(kind="ADD", description="NEEDLE 22G X 1.5IN", quantity="1", source="PCO1 ADD:X")]
    results = run_label_revision_check(old, new, expected, LADDER, TH, sku="1295108NS")
    added = [r for r in results if r.source_b is not None and r.source_b.description.startswith("Needle")]
    assert len(added) == 1 and added[0].classification is not Classification.EXACT and added[0].requires_validation


def test_numeric_guard_flags_partially_overlapping_numbers():
    s = similarity(normalize("NEEDLE 22G X 1.5IN"), normalize("Needle 22G x 1in"))
    assert s.numeric_conflict is True
    assert similarity(normalize("GAUZE 4X4"), normalize("Gauze, 10 cm x 10 cm (4 in. x 4 in.)")).numeric_conflict is False


def test_substitute_old_description_comes_from_bom():
    pco = pco_doc(["1295108NS"], [("SUBSTITUTE", "2370001", "2370002", "SHERLOCK SENSOR HOLDER V2", "1", "7")])
    bom = bom_doc([("2370001", "SHERLOCK SENSOR HOLDER", "1")])
    changes = expected_changes_from_pcos([pco], "1295108NS", boms=[bom])
    assert changes[0].kind == "SUBSTITUTE" and changes[0].old_description == "SHERLOCK SENSOR HOLDER"


# 3. PCO DELETE: "never found" is not proof of deletion
def test_pco_delete_absent_item_with_similar_description_under_other_number_is_potential():
    pco = pco_doc(["A"], [("DELETE", "2300001", "", "GLOVES EXAM", "", "")])
    bom = bom_doc([("2300001NS", "GLOVES EXAM", "1")], parent="A")
    r = [x for x in run_pco_bom_check(pco, [bom], LADDER, TH) if x.role != "coverage"][0]
    assert r.classification is Classification.POTENTIAL and r.requires_validation
    assert "2300001NS" in r.explanation


def test_pco_delete_with_skipped_bom_page_is_potential_and_expired_row_is_exact():
    pco = pco_doc(["A", "B"], [("DELETE", "RM5002565", "", "SCISSORS", "", "")])
    skipped = bom_doc([("0396447", "ABSORBENT TOWEL", "1")], parent="A")
    skipped.warnings.append("page 2: image-only page (scanned BOM?); OCR for BOM prints is NOT IMPLEMENTED — page skipped")
    expired = bom_doc([("RM5002565", "SCISSORS", "1", ItemCategory.PHYSICAL_COMPONENT, False)], parent="B")
    rows = {x.sku: x for x in run_pco_bom_check(pco, [skipped, expired], LADDER, TH) if x.role != "coverage"}
    assert rows["A"].classification is Classification.POTENTIAL and "skipped" in rows["A"].explanation
    assert rows["B"].classification is Classification.EXACT and "inactive" in rows["B"].explanation.lower()


# 4. Row ids must be unique when a set holds two labels / drawings
def test_row_ids_unique_with_two_current_labels_in_one_set(tmp_path):
    render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "sku-001" / "bom.pdf")
    render_label_pdf(LabelSpec(ref="1295108", product_name="Unit", contents=["1 Each - Towel, Absorbent"]), tmp_path / "sku-001" / "label_unit.pdf")
    render_label_pdf(LabelSpec(ref="1295108", product_name="Case", contents=["1 Each - Towel, Absorbent"]), tmp_path / "sku-001" / "label_case.pdf")
    run = run_folder(tmp_path, RelationshipStore.default(), TH)
    ids = [r.row_id for r in run.results]
    assert len(ids) == len(set(ids)) and len(ids) >= 4


# 5. Run identity must change when parser code changes
def test_run_id_includes_parser_versions(tmp_path, monkeypatch):
    render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "s" / "bom.pdf")
    render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), tmp_path / "s" / "label.pdf")
    a = run_folder(tmp_path, RelationshipStore.default(), TH).metadata.run_id
    monkeypatch.setattr("kaizen.ingest.bom_pdf.PARSER_VERSION", "999")
    b = run_folder(tmp_path, RelationshipStore.default(), TH).metadata.run_id
    assert a != b


# 6. Same item on two operation sequences
def test_pco_modify_uses_the_matching_sequence_row_and_flags_ambiguity_without_seq():
    pco = pco_doc(["A", "B"], [("MODIFY", "4400001", "4400001", "PART", "2", "20")])
    bom_a = bom_doc([("4400001", "PART", "2"), ("4400001", "PART", "1")], parent="A")
    bom_a.items[0].oper_seq, bom_a.items[1].oper_seq = "10.00", "20.00"
    r = [x for x in run_pco_bom_check(pco, [bom_a], LADDER, TH) if x.role != "coverage"][0]
    assert r.classification is Classification.MISMATCH and r.source_b.oper_seq == "20.00"  # seq-20 row still has qty 1
    pco2 = pco_doc(["A"], [("MODIFY", "4400001", "4400001", "PART", "2", "")])
    r2 = [x for x in run_pco_bom_check(pco2, [bom_a], LADDER, TH) if x.role != "coverage"][0]
    assert r2.classification is Classification.POTENTIAL and "2 rows" in r2.explanation


# 7. Category keywords must not swallow physical components; exclusions must be visible
@pytest.mark.parametrize("desc, expected", [
    ("STYLET INSERT 5F", ItemCategory.PHYSICAL_COMPONENT),
    ("MARKER SKIN INK BLUE", ItemCategory.PHYSICAL_COMPONENT),
    ("BOX, SHARPS DISPOSAL", ItemCategory.PHYSICAL_COMPONENT),
    ("INSERT, FOAM TRAY", ItemCategory.PACKAGING),
    ("IFU, CATH TRIMMING DEVICE", ItemCategory.DOCUMENT),
    ("PACKAGE INSERT, ENGLISH", ItemCategory.DOCUMENT),
    ("LOD THERMAL TRANSFER RIBBON", ItemCategory.PROCESS),
    ("TRAY, THERMOFORMED", ItemCategory.PACKAGING),
    ("BOX, SHIPPING", ItemCategory.PACKAGING),
])
def test_category_keywords_are_phrase_level(desc, expected):
    assert categorize("1234567", desc, Decimal("1"))[0] is expected


def test_excluded_bom_lines_appear_as_exempt_rows():
    bom = bom_doc([("BAW0724416", "EN LOD, UNIT LABEL", "1", ItemCategory.LABEL), ("0396447", "ABSORBENT TOWEL", "1")])
    results = run_bom_label_check(bom, label_doc([("Towel, Absorbent", "1")]), LADDER, TH)
    exempt = [r for r in results if r.role == "exempt"]
    assert len(exempt) == 1 and exempt[0].source_a.item_number == "BAW0724416"
    assert exempt[0].classification is Classification.EXACT and not exempt[0].requires_validation and "LABEL" in exempt[0].explanation


# 8. Anchored relationships must still look at the BOM wording
def test_anchor_with_unknown_bom_wording_needs_confirmation():
    store = RelationshipStore([Relationship(id="REL-1", canonical="Gloves", aliases=["GLOVES EXAM"], item_anchors=["2300001"])])
    lad = MatchLadder(store, TH)
    known = run_bom_label_check(bom_doc([("2300001", "GLOVES EXAM", "1")]), label_doc([("Gloves", "1")]), lad, TH)
    unknown = run_bom_label_check(bom_doc([("2300001", "ANYTHING AT ALL", "1")]), label_doc([("Gloves", "1")]), lad, TH)
    k = [r for r in known if r.role == "item"][0]
    u = [r for r in unknown if r.role == "item"][0]
    assert k.classification is Classification.EQUIVALENT and not k.requires_validation
    assert u.classification is Classification.POTENTIAL and u.requires_validation and u.relationship_id == "REL-1"
    assert "not a known term" in u.explanation


# 9. Duplicate BOM parents are all evaluated and flagged
def test_pco_evaluates_every_bom_with_the_same_parent_and_warns():
    pco = pco_doc(["A"], [("DELETE", "RM5002565", "", "SCISSORS", "", "")])
    b1 = bom_doc([("0396447", "ABSORBENT TOWEL", "1")], parent="A")
    b2 = bom_doc([("RM5002565", "SCISSORS", "1")], parent="A")
    b2.items[0].id, b2.id = "bom:2:r1", "bom:2"
    results = run_pco_bom_check(pco, [b1, b2], LADDER, TH)
    cov = [r for r in results if r.role == "coverage"]
    assert any("2 BOM" in r.explanation and r.requires_validation for r in cov)
    changes = [r for r in results if r.role != "coverage"]
    assert {r.classification for r in changes} == {Classification.EXACT, Classification.MISMATCH}


# 10. Concurrent writes to the workspace database must not interleave
def test_concurrent_decisions_are_all_recorded(tmp_path):
    ws = Workspace(tmp_path / "ws")
    store = ReviewStore(ws.db)
    errors = []

    def work(i):
        try:
            store.decide("run-x", f"R-{i:03d}", slot=1, reviewer=f"r{i}", decision="ACCEPT")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(25)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert len(store.all_decisions("run-x")) == 25
    assert hasattr(ws.db, "lock")


# 11. Thousands separators in quantities
def test_quantities_with_thousands_separators_parse(tmp_path):
    path = render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL", qty_per="1,000.0000", ext_qty="1,000.000000")]), tmp_path / "b.pdf")
    doc = parse_bom_pdf(path)
    assert doc.items[0].quantity == Decimal("1000.0000") and doc.items[0].extraction_confidence == 1.0
    assert parse_label_line("1,000 Each - Widget").quantity == Decimal("1000")


# 12. Exempt / header rows must not inflate the business case
def test_business_case_counts_only_reviewable_rows(tmp_path):
    render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="BAW0724416", description="EN LOD, UNIT LABEL"), BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "s" / "bom.pdf")
    render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), tmp_path / "s" / "label.pdf")
    run = run_folder(tmp_path, RelationshipStore.default(), TH)
    bc = business_case(run)
    reviewable = [r for r in run.results if r.role in ("item", "change")]
    assert bc.rows == len(reviewable) == 1
    assert bc.auto_cleared == 1 and bc.needs_validation == 0

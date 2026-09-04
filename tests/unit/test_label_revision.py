"""Phase 5: Old ↔ New label as a semantic change report, expected changes derived from PCOs."""

from kaizen.checks.label_revision import ExpectedChange, expected_changes_from_pcos, run_label_revision_check
from kaizen.matching.ladder import MatchLadder
from kaizen.models import CheckType, Classification, DiscrepancyType, Severity, Thresholds
from kaizen.terminology.store import RelationshipStore
from tests.unit.test_bom_label_check import label_doc
from tests.unit.test_pco_bom_check import pco_doc

TH = Thresholds()


def run(old, new, expected=()):
    return run_label_revision_check(old, new, list(expected), MatchLadder(RelationshipStore.default(), TH), TH, sku="1295108NS")


def by_change(results):
    return {r.source_a.attributes.get("change_key") if r.source_a is not None and "change_key" in r.source_a.attributes else r.explanation.split(":")[0]: r for r in results}


def keys(results):
    return {(r.role, r.classification.value, tuple(d.type.value for d in r.discrepancies)) for r in results}


def test_unchanged_lines_are_exact_and_auto_cleared():
    old = label_doc([("Towel, Absorbent", "1"), ("Mask", "2")])
    new = label_doc([("Towel, Absorbent", "1"), ("Mask", "2")])
    results = run(old, new)
    assert all(r.check is CheckType.LABEL_REVISION for r in results)
    lines = [r for r in results if r.role == "item"]
    assert len(lines) == 2 and all(r.classification is Classification.EXACT and not r.requires_validation for r in lines)
    assert "unchanged" in lines[0].explanation.lower()


def test_unexpected_addition_removal_and_quantity_change():
    old = label_doc([("Towel, Absorbent", "1"), ("Scissors with Protector Tubing", "1"), ("Gauze, 10 cm x 10 cm (4 in. x 4 in.)", "10")])
    new = label_doc([("Towel, Absorbent", "1"), ("Lubricating Jelly, 5 g", "1"), ("Gauze, 10 cm x 10 cm (4 in. x 4 in.)", "8")])
    results = run(old, new)
    changes = [r for r in results if r.discrepancies]
    kinds = {r.explanation.split(":")[0] for r in changes}
    assert kinds == {"REMOVED", "ADDED", "QUANTITY CHANGED"}
    assert all(d.type is DiscrepancyType.UNEXPECTED_LABEL_CHANGE and d.severity is Severity.MAJOR for r in changes for d in r.discrepancies)
    assert all(r.classification is Classification.MISMATCH and r.requires_validation for r in changes)
    qty = next(r for r in changes if r.explanation.startswith("QUANTITY CHANGED"))
    assert "10" in qty.explanation and "8" in qty.explanation
    assert qty.source_a.description.startswith("Gauze") and qty.source_b.description.startswith("Gauze")


def test_expected_changes_from_pco_are_recognised():
    old = label_doc([("Towel, Absorbent", "1"), ("Scissors with Protector Tubing", "1")])
    new = label_doc([("Towel, Absorbent", "1"), ("Catheter Trimming Device", "1")])
    expected = [ExpectedChange(kind="REMOVE", description="SCISSORS WITH PROTECTOR TUBING", source="PCO34590 DELETE:RM5002565"), ExpectedChange(kind="ADD", description="CATHETER TRIMMING DEVICE", quantity="1", source="PCO34590 ADD:RM0737876")]
    results = run(old, new, expected)
    changed = [r for r in results if r.role == "change"]
    assert len(changed) == 2
    assert all(r.classification is Classification.EXACT and not r.discrepancies for r in changed)
    assert all("EXPECTED" in r.explanation and "PCO34590" in r.explanation for r in changed)


def test_expected_change_absent_is_reported_with_pco_evidence():
    old = label_doc([("Towel, Absorbent", "1")])
    new = label_doc([("Towel, Absorbent", "1")])
    expected = [ExpectedChange(kind="ADD", description="CATHETER TRIMMING DEVICE", quantity="1", source="PCO34590 ADD:RM0737876")]
    results = run(old, new, expected)
    absent = [r for r in results if any(d.type is DiscrepancyType.EXPECTED_CHANGE_ABSENT for d in r.discrepancies)]
    assert len(absent) == 1
    assert absent[0].classification is Classification.MISSING and absent[0].requires_validation
    assert "PCO34590" in absent[0].discrepancies[0].detail and "CATHETER TRIMMING DEVICE" in absent[0].discrepancies[0].detail


def test_expected_add_already_present_on_old_label_is_satisfied():
    old = label_doc([("Towel, Absorbent", "1"), ("Catheter Trimming Device", "1")])
    new = label_doc([("Towel, Absorbent", "1"), ("Catheter Trimming Device", "1")])
    expected = [ExpectedChange(kind="ADD", description="CATHETER TRIMMING DEVICE", quantity="1", source="PCO34590 ADD:RM0737876")]
    results = run(old, new, expected)
    assert not any(r.discrepancies for r in results)
    assert any("already present" in r.explanation.lower() for r in results)


def test_substitution_expected_as_description_change():
    old = label_doc([("Sherlock™ Sensor Holder", "1")])
    new = label_doc([("Sherlock™ Sensor Holder V2", "1")])
    expected = [ExpectedChange(kind="SUBSTITUTE", description="SHERLOCK SENSOR HOLDER V2", old_description="SHERLOCK SENSOR HOLDER", quantity="1", source="PCO34591 SUBSTITUTE:2370001>2370002")]
    results = run(old, new, expected)
    change = [r for r in results if r.role == "change"]
    assert len(change) == 1 and change[0].classification is Classification.EXACT
    assert "DESCRIPTION CHANGED" in change[0].explanation and "EXPECTED" in change[0].explanation


def test_ref_change_is_unexpected():
    old = label_doc([("Towel, Absorbent", "1")], ref="1295108")
    new = label_doc([("Towel, Absorbent", "1")], ref="1295109")
    results = run(old, new)
    header = [r for r in results if r.role == "header"][0]
    assert header.classification is Classification.MISMATCH
    assert header.discrepancies[0].type is DiscrepancyType.UNEXPECTED_LABEL_CHANGE and "REF" in header.discrepancies[0].detail


def test_expected_changes_from_pcos_filters_by_sku_and_physical_items():
    pco = pco_doc(["1295108NS", "1395108QNS"], [("DELETE", "RM5002565", "", "SCISSORS WITH PROTECTOR TUBING", "", ""), ("ADD", "", "RM0737876", "CATHETER TRIMMING DEVICE", "1", "7"), ("ADD", "", "PK0744425", "IFU, CATH TRIMMING DEVICE", "1", "7")])
    changes = expected_changes_from_pcos([pco], "1295108NS")
    assert [(c.kind, c.description) for c in changes] == [("REMOVE", "SCISSORS WITH PROTECTOR TUBING"), ("ADD", "CATHETER TRIMMING DEVICE")]
    assert all("PCO34590" in c.source for c in changes)
    assert expected_changes_from_pcos([pco], "9999999NS") == []

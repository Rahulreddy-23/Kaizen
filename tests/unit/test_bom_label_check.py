from decimal import Decimal

from kaizen.checks.bom_label import run_bom_label_check
from kaizen.matching.ladder import MatchLadder
from kaizen.models import (
    CheckType,
    Classification,
    DiscrepancyType,
    DocType,
    Document,
    DocumentItem,
    Evidence,
    ItemCategory,
    MatchLevel,
    Relationship,
    Severity,
    SubQuantity,
    Thresholds,
)
from kaizen.terminology.store import RelationshipStore

SHA = "ab" * 32
TH = Thresholds()
STORE = RelationshipStore([Relationship(id="REL-001", canonical="Surgical Tape", aliases=["TAPE ANCHOR PER-Q-CATH"])])


def bom_doc(rows, parent="1295108NS", parent_desc="POWERPICC KIT"):
    items = []
    for n, row in enumerate(rows, start=1):
        item, desc, qty = row[:3]
        category = row[3] if len(row) > 3 else ItemCategory.PHYSICAL_COMPONENT
        active = row[4] if len(row) > 4 else True
        confidence = row[5] if len(row) > 5 else 1.0
        items.append(
            DocumentItem(
                id=f"bom:1:r{n}", doc_id="bom:1", doc_type=DocType.BOM, sku=parent, item_number=item, description=desc,
                quantity=Decimal(qty) if qty is not None else None, uom="EA", category=category, category_reason="test", is_active=active,
                extraction_confidence=confidence,
                evidence=Evidence(file="sku/bom.pdf", file_sha256=SHA, page=1, raw_text=f"{item} {desc} {qty}", locator=f"page 1, row {n}"),
            )
        )
    return Document(id="bom:1", doc_type=DocType.BOM, path="sku/bom.pdf", sha256=SHA, sku=parent, header={"parent_item": parent, "parent_description": parent_desc}, items=items, parser_name="t", parser_version="1")


def label_doc(lines, ref="1295108"):
    items = []
    for n, row in enumerate(lines, start=1):
        desc, qty = row[:2]
        sub = row[2] if len(row) > 2 else None
        items.append(
            DocumentItem(
                id=f"label:1:c1e{n}", doc_id="label:1", doc_type=DocType.LABEL, sku=ref, description=desc, quantity=Decimal(qty), uom="EACH",
                sub_quantity=sub, category=ItemCategory.PHYSICAL_COMPONENT, category_reason="label line",
                evidence=Evidence(file="sku/label.pdf", file_sha256=SHA, page=1, raw_text=f"{qty} Each - {desc}", locator=f"page 1, entry {n}"),
            )
        )
    return Document(id="label:1", doc_type=DocType.LABEL, path="sku/label.pdf", sha256=SHA, sku=ref, header={"ref": ref}, items=items, parser_name="t", parser_version="1")


def run(bom, label):
    return run_bom_label_check(bom, label, MatchLadder(STORE, TH), TH)


def by_item(results):
    return {r.source_a.item_number: r for r in results if r.source_a is not None and r.role == "item"}


def test_exact_pair_has_no_discrepancy_and_needs_no_validation():
    res = by_item(run(bom_doc([("0396447", "ABSORBENT TOWEL", "1")]), label_doc([("Towel, Absorbent", "1")])))
    r = res["0396447"]
    assert r.classification is Classification.EXACT
    assert r.match_level is MatchLevel.EXACT
    assert r.discrepancies == [] and r.requires_validation is False
    assert "EXACT" in r.explanation and "quantity" in r.explanation.lower()
    assert r.normalized_a == "ABSORBENT TOWEL" and r.normalized_b == "TOWEL ABSORBENT"
    assert r.source_b.description == "Towel, Absorbent"
    assert r.check is CheckType.BOM_LABEL and r.sku == "1295108NS"


def test_relationship_pair_is_equivalent_with_id():
    r = by_item(run(bom_doc([("5167473", "TAPE ANCHOR PER-Q-CATH", "1")]), label_doc([("Surgical Tape", "1")])))["5167473"]
    assert r.classification is Classification.EQUIVALENT
    assert r.relationship_id == "REL-001"
    assert r.requires_validation is False


def test_quantity_mismatch_on_equivalent_pair_is_mismatch():
    r = by_item(run(bom_doc([("5167473", "TAPE ANCHOR PER-Q-CATH", "2")]), label_doc([("Surgical Tape", "1")])))["5167473"]
    assert r.classification is Classification.MISMATCH
    assert r.discrepancies[0].type is DiscrepancyType.QTY_MISMATCH
    assert r.discrepancies[0].severity is Severity.MAJOR
    assert r.requires_validation is True
    assert r.relationship_id == "REL-001"


def test_idiom_explainable_quantity_is_potential_not_mismatch():
    r = by_item(run(bom_doc([("2220001", "TAPE STRIPS", "6")]), label_doc([("Tape Strips", "2", SubQuantity(value=3, kind="per", raw="(3 per)"))])))["2220001"]
    assert r.classification is Classification.POTENTIAL
    assert r.discrepancies[0].type is DiscrepancyType.QTY_MISMATCH
    assert r.discrepancies[0].severity is Severity.MINOR
    assert "3 per" in r.discrepancies[0].detail
    assert r.requires_validation is True


def test_potential_pair_with_qty_difference_keeps_potential_and_notes_qty():
    r = by_item(run(bom_doc([("3330001", "CHLORAPREP APPLICATOR 3ML", "2")]), label_doc([("ChloraPrep Solution One-Step Applicator, 3 mL", "1")])))["3330001"]
    assert r.classification is Classification.POTENTIAL
    assert r.match_level is MatchLevel.FUZZY
    assert any(d.type is DiscrepancyType.QTY_MISMATCH for d in r.discrepancies)
    assert r.requires_validation is True


def test_missing_in_label_with_hint():
    r = by_item(run(bom_doc([("0396447", "ABSORBENT TOWEL", "1")]), label_doc([("Drape, Absorbent", "1")])))["0396447"]
    assert r.classification is Classification.MISSING
    assert r.source_b is None
    assert r.discrepancies[0].type is DiscrepancyType.MISSING_IN_LABEL
    assert "Drape, Absorbent" in r.discrepancies[0].detail  # closest candidate offered to the reviewer
    assert r.requires_validation is True


def test_extra_label_line_is_missing_in_bom():
    results = run(bom_doc([("0396447", "ABSORBENT TOWEL", "1")]), label_doc([("Towel, Absorbent", "1"), ("Mystery Widget", "1")]))
    extra = [r for r in results if r.source_a is None]
    assert len(extra) == 1
    assert extra[0].classification is Classification.MISSING
    assert extra[0].discrepancies[0].type is DiscrepancyType.MISSING_IN_BOM
    assert extra[0].source_b.description == "Mystery Widget"


def test_non_physical_and_inactive_rows_are_not_compared():
    bom = bom_doc(
        [
            ("BAW0724416", "EN LOD, UNIT LABEL", "1", ItemCategory.LABEL),
            ("MPS0090", "PRODUCING LABELS ON THE", "0", ItemCategory.PROCESS),
            ("7770001", "GAUZE 4X4", "10", ItemCategory.PHYSICAL_COMPONENT, False),
            ("0703450", "LOD THERMAL TRANSFER RIBBON", "0", ItemCategory.PHYSICAL_COMPONENT),
            ("0396447", "ABSORBENT TOWEL", "1"),
        ]
    )
    results = run(bom, label_doc([("Towel, Absorbent", "1")]))
    items = by_item(results)
    assert set(items) == {"0396447"}
    assert all(d.type is not DiscrepancyType.MISSING_IN_LABEL for r in results for d in r.discrepancies)


def test_ambiguous_match_is_flagged():
    r = by_item(run(bom_doc([("4440001", "NEEDLE 21G", "1")]), label_doc([("Needle, Introducer, 21 G", "1"), ("Needle, Safety Hypodermic, 21 G", "1")])))["4440001"]
    assert r.classification is Classification.POTENTIAL
    assert any(d.type is DiscrepancyType.AMBIGUOUS_MATCH for d in r.discrepancies)
    assert "Safety Hypodermic" in " ".join(d.detail for d in r.discrepancies)
    assert r.requires_validation is True


def test_ref_parent_row_family_match():
    results = run(bom_doc([("0396447", "ABSORBENT TOWEL", "1")]), label_doc([("Towel, Absorbent", "1")]))
    header = results[0]
    assert header.source_a.attributes["kind"] == "header"
    assert header.classification is Classification.EXACT
    assert "1295108NS" in header.explanation and "1295108" in header.explanation


def test_ref_parent_mismatch_is_blocker():
    results = run(bom_doc([("0396447", "ABSORBENT TOWEL", "1")]), label_doc([("Towel, Absorbent", "1")], ref="9999999"))
    header = results[0]
    assert header.classification is Classification.MISMATCH
    assert header.discrepancies[0].type is DiscrepancyType.REF_PARENT_MISMATCH
    assert header.discrepancies[0].severity is Severity.BLOCKER


def test_low_extraction_confidence_is_flagged():
    r = by_item(run(bom_doc([("0396447", "ABSORBENT TOWEL", "1", ItemCategory.PHYSICAL_COMPONENT, True, 0.5)]), label_doc([("Towel, Absorbent", "1")])))["0396447"]
    assert any(d.type is DiscrepancyType.LOW_EXTRACTION_CONFIDENCE for d in r.discrepancies)
    assert r.requires_validation is True


def test_row_ids_unique_and_prefixed_and_every_row_explained():
    results = run(
        bom_doc([("0396447", "ABSORBENT TOWEL", "1"), ("5167473", "TAPE ANCHOR PER-Q-CATH", "1"), ("9990001", "UNLISTED PART", "1")]),
        label_doc([("Towel, Absorbent", "1"), ("Surgical Tape", "1"), ("Mystery Widget", "1")]),
    )
    ids = [r.row_id for r in results]
    assert len(ids) == len(set(ids)) == 5
    assert all(i.startswith("R-1295108NS-") for i in ids)
    assert all(r.explanation.strip() for r in results)
    assert [r.classification for r in results] == [Classification.EXACT, Classification.EXACT, Classification.EQUIVALENT, Classification.MISSING, Classification.MISSING]

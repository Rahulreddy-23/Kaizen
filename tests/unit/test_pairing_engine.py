"""The shared pairing engine every presence/identity check is built on."""

from kaizen.checks.pairing import CheckPolicy, run_pairing_check
from kaizen.matching.ladder import MatchLadder
from kaizen.models import CheckType, Classification, DiscrepancyType, DocType, Document, DocumentItem, Evidence, ItemCategory, Severity, Thresholds
from kaizen.terminology.store import RelationshipStore
from tests.unit.test_bom_label_check import SHA, bom_doc, label_doc

TH = Thresholds()


def drawing_doc(callouts, number="DWG3173108", rev="11"):
    items = []
    for n, c in enumerate(callouts, start=1):
        desc, conditional = (c, False) if isinstance(c, str) else c
        items.append(DocumentItem(id=f"dwg:1:c{n}", doc_id="dwg:1", doc_type=DocType.DRAWING, sku=number, description=desc, category=ItemCategory.PHYSICAL_COMPONENT, category_reason="callout", attributes={"kind": "callout", "conditional": conditional, "es_text": ""}, evidence=Evidence(file="sku/drawing.pdf", file_sha256=SHA, page=1, raw_text=desc, locator=f"page 1, callout {n}")))
    return Document(id="dwg:1", doc_type=DocType.DRAWING, path="sku/drawing.pdf", sha256=SHA, sku=number, header={"drawing_number": number, "revision": rev, "title": "TRAY"}, items=items, parser_name="t", parser_version="1")


PRESENCE = CheckPolicy(check_type=CheckType.BOM_DRAWING, row_letter="D", quantity_relevant=False, missing_a=DiscrepancyType.MISSING_IN_DRAWING, missing_b=DiscrepancyType.EXTRA_ON_DRAWING, a_label="BOM component", b_label="drawing callout", conditional_b_exempt=True)


def run(a_doc, a_items, b_doc, b_items, policy=PRESENCE):
    return run_pairing_check(a_doc, a_items, b_doc, b_items, policy, MatchLadder(RelationshipStore.default(), TH), TH, sku="1295108NS")


def test_presence_policy_ignores_quantities():
    bom = bom_doc([("2260001", "END CAP", "2"), ("0396447", "ABSORBENT TOWEL", "1")])
    dwg = drawing_doc(["END CAPS", "ABSORBENT TOWEL"])
    rows = {r.source_a.item_number: r for r in run(bom, bom.items, dwg, dwg.items) if r.source_a}
    assert rows["2260001"].classification is Classification.EXACT and rows["2260001"].discrepancies == []
    assert "quantity" not in rows["2260001"].explanation.lower()
    assert rows["0396447"].classification is Classification.EXACT


def test_missing_on_each_side_uses_policy_types():
    bom = bom_doc([("2330001", "TOURNIQUET", "1")])
    dwg = drawing_doc(["FILTER STRAW"])
    results = run(bom, bom.items, dwg, dwg.items)
    a = [r for r in results if r.source_a is not None][0]
    b = [r for r in results if r.source_a is None][0]
    assert a.discrepancies[0].type is DiscrepancyType.MISSING_IN_DRAWING and a.discrepancies[0].severity is Severity.MAJOR
    assert b.discrepancies[0].type is DiscrepancyType.EXTRA_ON_DRAWING
    assert "BOM component" in a.discrepancies[0].detail and "drawing callout" in b.discrepancies[0].detail


def test_conditional_callout_without_bom_item_is_exempt():
    bom = bom_doc([("2330001", "TOURNIQUET", "1")])
    dwg = drawing_doc(["TOURNIQUET", ("SHARP HOLDER", True)])
    results = run(bom, bom.items, dwg, dwg.items)
    extra = [r for r in results if r.source_a is None]
    assert len(extra) == 1
    assert extra[0].classification is Classification.EXACT
    assert extra[0].discrepancies == [] and extra[0].requires_validation is False
    assert "conditional" in extra[0].explanation.lower()


def test_conditional_callout_with_bom_item_pairs_normally():
    bom = bom_doc([("2360001", "SHARP HOLDER", "1")])
    dwg = drawing_doc([("SHARP HOLDER", True)])
    rows = [r for r in run(bom, bom.items, dwg, dwg.items) if r.source_a is not None]
    assert rows[0].classification is Classification.EXACT and rows[0].source_b is not None


def test_relationship_and_fuzzy_levels_and_row_ids():
    bom = bom_doc([("5167473", "TAPE ANCHOR PER-Q-CATH", "1"), ("4460021", "NEEDLE INTRODUCER 21G", "1")])
    dwg = drawing_doc(["SURGICAL TAPE", "INTRODUCER NEEDLE 21 GA"])
    results = run(bom, bom.items, dwg, dwg.items)
    rows = {r.source_a.item_number: r for r in results if r.source_a}
    assert rows["5167473"].classification is Classification.EQUIVALENT and rows["5167473"].relationship_id == "REL-001"
    assert rows["4460021"].classification is Classification.POTENTIAL
    assert all(r.row_id.startswith("D-1295108NS-") for r in results) and all(r.check is CheckType.BOM_DRAWING for r in results)


def test_quantity_policy_reproduces_bom_label_behaviour():
    policy = CheckPolicy(check_type=CheckType.BOM_LABEL, row_letter="R", quantity_relevant=True, missing_a=DiscrepancyType.MISSING_IN_LABEL, missing_b=DiscrepancyType.MISSING_IN_BOM, a_label="BOM component", b_label="label line")
    bom = bom_doc([("2260001", "END CAP", "2")])
    lab = label_doc([("End Cap", "1")])
    r = run(bom, bom.items, lab, lab.items, policy)[0]
    assert r.classification is Classification.MISMATCH and r.discrepancies[0].type is DiscrepancyType.QTY_MISMATCH


def test_label_vs_drawing_without_item_numbers():
    policy = CheckPolicy(check_type=CheckType.LABEL_DRAWING, row_letter="L", quantity_relevant=False, missing_a=DiscrepancyType.MISSING_IN_DRAWING, missing_b=DiscrepancyType.EXTRA_ON_DRAWING, a_label="label line", b_label="drawing callout", conditional_b_exempt=True)
    lab = label_doc([("Measuring Tape", "2"), ("Safety Scalpel", "1")])
    dwg = drawing_doc(["TAPE MEASURE", "SCALPEL SAFETY"])
    results = run(lab, lab.items, dwg, dwg.items, policy)
    assert [r.classification for r in results] == [Classification.EQUIVALENT, Classification.EXACT]
    assert results[0].relationship_id == "REL-002"

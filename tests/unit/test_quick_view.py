"""Three-source views must preserve evidence without inventing matches."""

import pytest

from kaizen.api.app import _evidence
from kaizen.api.quick_view import build_quick_view, filter_quick_view
from kaizen.models import BBox, CheckResult, Classification, Document, DocumentItem, Evidence, Run, RunMetadata, SkuGroup


def fixture():
    docs = []
    for kind in ("BOM", "LABEL", "DRAWING"):
        item = DocumentItem(
            id=f"{kind}:one",
            doc_id=kind,
            doc_type=kind,
            description=f"{kind} protective cover",
            category="PHYSICAL_COMPONENT",
            item_number="PART-A" if kind == "BOM" else None,
            quantity="1" if kind != "DRAWING" else None,
            uom="EA",
            evidence=Evidence(file=f"{kind}.pdf", file_sha256="a" * 64, page=1, raw_text=f"{kind} original text", locator="row 1", bbox=BBox(x0=20, y0=30, x1=100, y1=40)),
        )
        docs.append(Document(id=kind, doc_type=kind, path=f"{kind}.pdf", sha256="a" * 64, items=[item], parser_name="synthetic", parser_version="1"))
    results = [
        CheckResult(
            row_id=f"pair{n}", sku="SKU-A", check=check, source_a=docs[a].items[0], source_b=docs[b].items[0], classification="EXACT", match_level="L1_EXACT", explanation="Saved exact pairing"
        )
        for n, (check, a, b) in enumerate([("BOM_LABEL", 0, 1), ("BOM_DRAWING", 0, 2), ("LABEL_DRAWING", 1, 2)])
    ]
    run = Run(
        metadata=RunMetadata(run_id="quick", tool_version="test", terminology_version="test", input_root="."),
        documents=docs,
        results=results,
        groups=[SkuGroup(sku="SKU-A", family="A", document_ids=[d.id for d in docs])],
    )
    return run


def snapshot(run):
    return [
        {
            "row_id": r.row_id,
            "effective_classification": r.classification.value,
            "pending_review": r.requires_validation,
            "unresolved": bool(r.discrepancies),
            "current_discrepancies": [],
            "state": "ENGINE_RECOMMENDED",
        }
        for r in run.results
    ]


def project(run, view="components", sku="SKU-A", snapshots=None):
    return build_quick_view(run, snapshots or snapshot(run), sku, view, _evidence)


def test_complete_pairings_align_all_three_original_sources():
    run = fixture()
    before = run.model_dump_json()
    data = project(run)
    assert len(data["rows"]) == 1 and data["rows"][0]["status"] == "matched"
    for kind, cell in data["rows"][0]["cells"].items():
        assert cell["status"] == "matched" and cell["items"][0]["doc_id"] == kind
        assert cell["items"][0]["page"] == 1 and cell["items"][0]["bbox"]["x0"] == 20
        assert cell["items"][0]["raw_text"] == f"{kind} original text"
    assert run.model_dump_json() == before


def test_conflicting_third_pair_is_not_cleared_through_transitivity():
    run = fixture()
    run.results[2].classification = Classification.MISMATCH
    run.results[2].requires_validation = True
    data = project(run)
    row = data["rows"][0]
    assert row["status"] == "attention"
    assert row["cells"]["LABEL"]["status"] == row["cells"]["DRAWING"]["status"] == "attention"
    assert row["cells"]["BOM"]["status"] == "matched"
    assert [c["status"] for c in row["checks"]].count("attention") == 1


def test_stored_exact_without_counterpart_and_exemptions_cannot_turn_green():
    run = fixture()
    run.results = run.results[:1]
    run.results[0].source_b = None
    data = project(run)
    assert data["rows"][0]["status"] == "attention"
    run.results[0].role = "exempt"
    data = project(run)
    assert data["rows"][0]["status"] == "neutral"
    assert data["rows"][0]["cells"]["LABEL"] is None


def test_current_approved_override_and_information_request_control_status():
    run = fixture()
    run.results[0].classification = Classification.POTENTIAL
    run.results[0].requires_validation = True
    current = snapshot(run)
    current[0].update(effective_classification="EXACT", pending_review=False, unresolved=False, state="FINALIZED")
    assert project(run, snapshots=current)["rows"][0]["status"] == "matched"
    current[0].update(pending_review=True)
    assert project(run, snapshots=current)["rows"][0]["status"] == "attention"


def test_shared_document_is_evaluated_in_each_sku_without_cross_sku_results():
    run = fixture()
    run.groups.append(SkuGroup(sku="SKU-B", family="B", document_ids=["DRAWING"]))
    run.results.append(run.results[1].model_copy(update={"row_id": "other", "sku": "SKU-B", "source_a": None, "requires_validation": True}))
    a = project(run)
    b = project(run, sku="SKU-B")
    assert a["rows"][0]["status"] == "matched"
    assert b["rows"][0]["status"] == "attention" and b["rows"][0]["cells"]["BOM"] is None
    assert len(b["documents"]) == 1


def test_all_text_keeps_headers_and_notes_neutral_and_retains_unparsed_words():
    run = fixture()
    doc = run.documents[1]
    item = doc.items[0]
    doc.text_lines = [
        item.model_copy(update={"id": "text:body", "description": "1 Each Protective Cover"}),
        item.model_copy(update={"id": "text:note", "description": "Keep dry; unknown wording", "evidence": item.evidence.model_copy(update={"bbox": BBox(x0=20, y0=80, x1=100, y1=90)})}),
    ]
    data = project(run, view="text")
    assert data["rows"][0]["cells"]["LABEL"]["status"] == "matched"
    assert data["rows"][1]["cells"]["LABEL"]["status"] == "neutral"
    assert data["rows"][1]["cells"]["LABEL"]["items"][0]["description"] == "Keep dry; unknown wording"
    assert all(r["status"] == "neutral" and not r["checks"] for r in data["rows"])


def test_duplicate_bom_source_rows_and_every_orphan_are_preserved():
    run = fixture()
    doc = run.documents[0]
    first = doc.items[0]
    second = first.model_copy(update={"id": "BOM:two", "evidence": first.evidence.model_copy(update={"locator": "row 2"})})
    doc.items.append(second)
    for r in run.results[:2]:
        r.source_a = first.model_copy(update={"attributes": {"merged_rows": 2, "merged_locators": ["row 1", "row 2"]}})
    data = project(run)
    assert len(data["rows"]) == 2
    assert {r["cells"]["BOM"]["items"][0]["id"] for r in data["rows"]} == {"BOM:one", "BOM:two"}
    orphan = first.model_copy(update={"id": "BOM:orphan", "item_number": "PART-B", "description": "Unknown tubing", "evidence": first.evidence.model_copy(update={"locator": "row 3"})})
    doc.items.append(orphan)
    data = project(run)
    assert any(r["cells"]["BOM"]["items"][0]["id"] == "BOM:orphan" and r["status"] == "neutral" for r in data["rows"])


def test_pagination_search_and_status_keep_counts_and_do_not_truncate_evidence():
    data = project(fixture())
    assert filter_quick_view(data, "all", "original text", 0, 1)["total"] == 1
    assert filter_quick_view(data, "matched", "", 1, 1)["rows"] == []
    assert filter_quick_view(data, "attention", "", 0, 1)["total"] == 0
    assert filter_quick_view(data, "all", "unrelated", 0, 1)["rows"] == []
    with pytest.raises(KeyError):
        project(fixture(), sku="nonexistent")

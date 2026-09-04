from decimal import Decimal

import pytest
from pydantic import ValidationError

from kaizen.models import (
    BBox,
    CheckResult,
    CheckType,
    Classification,
    Discrepancy,
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
)


def make_evidence(**overrides) -> Evidence:
    base = dict(file="sku-001/bom.pdf", file_sha256="ab" * 32, page=1, raw_text="0396447 ABSORBENT TOWEL 1.0000")
    base.update(overrides)
    return Evidence(**base)


def make_item(**overrides) -> DocumentItem:
    base = dict(
        id="bom-1",
        doc_id="doc-bom-1",
        doc_type=DocType.BOM,
        sku="1295108NS",
        item_number="0396447",
        description="ABSORBENT TOWEL",
        quantity=Decimal("1.0000"),
        uom="EA",
        category=ItemCategory.PHYSICAL_COMPONENT,
        evidence=make_evidence(),
    )
    base.update(overrides)
    return DocumentItem(**base)


def test_document_item_keeps_evidence_and_defaults():
    item = make_item()
    assert item.evidence.page == 1
    assert item.is_active is True
    assert item.extraction_confidence == 1.0
    assert item.attributes == {}
    assert item.sub_quantity is None


def test_document_item_requires_evidence():
    with pytest.raises(ValidationError):
        DocumentItem(
            id="x", doc_id="d", doc_type=DocType.LABEL, description="Towel", category=ItemCategory.UNKNOWN
        )


def test_extraction_confidence_bounded():
    with pytest.raises(ValidationError):
        make_item(extraction_confidence=1.5)
    with pytest.raises(ValidationError):
        make_item(extraction_confidence=-0.1)


def test_quantity_coerces_to_decimal_and_allows_none():
    assert make_item(quantity="0.4000").quantity == Decimal("0.4000")
    assert make_item(quantity=None).quantity is None


def test_bbox_rejects_inverted_box():
    with pytest.raises(ValidationError):
        BBox(x0=10, y0=10, x1=5, y1=20)


def test_sub_quantity_model():
    sq = SubQuantity(value=3, kind="per", raw="(3 per)")
    assert sq.value == 3


def test_document_holds_items_and_sha():
    doc = Document(
        id="doc-bom-1",
        doc_type=DocType.BOM,
        path="sku-001/bom.pdf",
        sha256="ab" * 32,
        sku="1295108NS",
        parser_name="bom_pdf",
        parser_version="1",
        items=[make_item()],
    )
    assert doc.items[0].item_number == "0396447"
    assert doc.warnings == []


def test_relationship_defaults_and_terms():
    rel = Relationship(id="REL-001", canonical="Surgical Tape", aliases=["Tape Anchor Per-Q-Cath", "Tape Measure"])
    assert rel.scope == "global"
    assert rel.active is True
    assert rel.provenance == "manual"
    assert set(rel.terms()) == {"Surgical Tape", "Tape Anchor Per-Q-Cath", "Tape Measure"}


def test_relationship_scope_must_be_well_formed():
    with pytest.raises(ValidationError):
        Relationship(id="REL-002", canonical="x", scope="banana")
    assert Relationship(id="REL-003", canonical="x", scope="family:1295108").scope == "family:1295108"
    assert Relationship(id="REL-004", canonical="x", scope="sku:1295108NS").scope == "sku:1295108NS"


def test_check_result_requires_explanation():
    with pytest.raises(ValidationError):
        CheckResult(
            row_id="R-1",
            sku="1295108NS",
            check=CheckType.BOM_LABEL,
            classification=Classification.EXACT,
            match_level=MatchLevel.EXACT,
            explanation="   ",
        )


def test_check_result_requires_validation_flag_and_discrepancies():
    disc = Discrepancy(
        type=DiscrepancyType.QTY_MISMATCH,
        severity=Severity.MAJOR,
        detail="BOM qty 2 vs label qty 1",
        recommended_action="Confirm which quantity is correct",
    )
    res = CheckResult(
        row_id="R-1",
        sku="1295108NS",
        check=CheckType.BOM_LABEL,
        source_a=make_item(quantity=Decimal("2")),
        source_b=make_item(id="lbl-1", doc_type=DocType.LABEL, item_number=None, description="Surgical Tape"),
        classification=Classification.MISMATCH,
        match_level=MatchLevel.RELATIONSHIP,
        score=1.0,
        relationship_id="REL-001",
        explanation="EQUIVALENT via REL-001 but quantity differs",
        discrepancies=[disc],
        requires_validation=True,
    )
    assert res.discrepancies[0].type is DiscrepancyType.QTY_MISMATCH
    assert res.reviewer_decision is None
    assert res.final_status == "OPEN"


def test_enums_cover_taxonomy():
    expected = {
        "QTY_MISMATCH", "DESC_MISMATCH", "MISSING_IN_LABEL", "MISSING_IN_BOM", "REF_PARENT_MISMATCH",
        "AMBIGUOUS_MATCH", "LOW_EXTRACTION_CONFIDENCE", "MISSING_IN_DRAWING", "EXTRA_ON_DRAWING",
        "PCO_CHANGE_NOT_APPLIED", "PCO_QTY_SEQ_MISMATCH", "BOM_MISSING_FOR_AFFECTED_CODE",
        "UNEXPECTED_LABEL_CHANGE", "EXPECTED_CHANGE_ABSENT", "DRAWING_REV_MISMATCH",
    }
    assert expected <= {d.name for d in DiscrepancyType}
    assert {c.name for c in Classification} == {"EXACT", "EQUIVALENT", "POTENTIAL", "MISMATCH", "MISSING"}
    assert {c.name for c in ItemCategory} >= {
        "PHYSICAL_COMPONENT", "PACKAGING", "LABEL", "PROCESS", "QUALITY", "ADMINISTRATIVE", "DOCUMENT", "UNKNOWN"
    }

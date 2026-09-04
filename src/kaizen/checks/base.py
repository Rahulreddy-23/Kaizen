"""Shared helpers for checks: row ids, classification mapping, recommended actions."""

from kaizen.models import Classification, DiscrepancyType, DocType, Document, DocumentItem, Evidence, ItemCategory, MatchLevel

CLASSIFICATION_BY_LEVEL = {
    MatchLevel.EXACT: Classification.EXACT,
    MatchLevel.RELATIONSHIP: Classification.EQUIVALENT,
    MatchLevel.FUZZY: Classification.POTENTIAL,
    MatchLevel.SEMANTIC: Classification.POTENTIAL,
    MatchLevel.LLM: Classification.POTENTIAL,
    MatchLevel.NONE: Classification.MISSING,
}

RECOMMENDED_ACTION = {
    DiscrepancyType.QTY_MISMATCH: "Confirm the correct quantity against the approved redline; correct the BOM or the label.",
    DiscrepancyType.DESC_MISMATCH: "Confirm the two descriptions refer to the same component; add a relationship if they do.",
    DiscrepancyType.MISSING_IN_LABEL: "Confirm whether this BOM component must appear on the label; if it does under another wording, add a relationship.",
    DiscrepancyType.MISSING_IN_BOM: "Confirm whether this label line corresponds to a BOM component under a different description.",
    DiscrepancyType.REF_PARENT_MISMATCH: "Verify the label belongs to this SKU before reviewing any other row.",
    DiscrepancyType.AMBIGUOUS_MATCH: "Select the correct label line; consider an item-anchored relationship to remove the ambiguity.",
    DiscrepancyType.LOW_EXTRACTION_CONFIDENCE: "Verify the extracted values against the source page.",
}


def pair_token(*doc_ids: str) -> str:
    """Short, stable token for the document pair a check ran on, so two labels or drawings in one SKU set never
    produce colliding row ids (decisions and action items are keyed by row id)."""
    import hashlib

    return hashlib.sha256("|".join(doc_ids).encode()).hexdigest()[:4]


class RowIdFactory:
    def __init__(self, sku: str, letter: str = "R", pair: str | None = None):
        self.sku = sku
        self.letter = letter
        self.pair = pair
        self.seq = 0

    def next(self) -> str:
        self.seq += 1
        mid = f"{self.pair}-" if self.pair else ""
        return f"{self.letter}-{self.sku}-{mid}{self.seq:03d}"


RECOMMENDED_ACTION.update(
    {
        DiscrepancyType.PCO_CHANGE_NOT_APPLIED: "Apply the PCO change to the BOM (or redline it) before release, or reject the PCO row.",
        DiscrepancyType.PCO_QTY_SEQ_MISMATCH: "Align the BOM quantity / operation sequence with the PCO proposal, or correct the PCO.",
        DiscrepancyType.BOM_MISSING_FOR_AFFECTED_CODE: "Download the BOM for this affected code from JDE and add it to the set before reviewing.",
        DiscrepancyType.MISSING_IN_DRAWING: "Confirm whether the component must be shown on the packaging drawing; update the drawing or the BOM.",
        DiscrepancyType.EXTRA_ON_DRAWING: "Confirm whether the drawing callout refers to a BOM component under another description or an obsolete item.",
        DiscrepancyType.DRAWING_REV_MISMATCH: "Confirm the drawing number / revision referenced by the BOM against the released drawing.",
        DiscrepancyType.UNEXPECTED_LABEL_CHANGE: "Confirm the change against the approved redline; it is not covered by the PCO.",
        DiscrepancyType.EXPECTED_CHANGE_ABSENT: "Apply the approved change to the new label revision or update the PCO.",
    }
)


def header_item(doc: Document, kind_desc: str) -> DocumentItem:
    """A pseudo-item representing a document's header (BOM parent, label REF, PCO number) so header-level
    results still carry evidence."""
    if doc.doc_type is DocType.BOM:
        code, desc, raw = doc.sku or "", doc.header.get("parent_description", ""), f"Parent Item {doc.sku or ''}"
    elif doc.doc_type is DocType.LABEL:
        code, desc, raw = doc.sku or "", doc.header.get("product_name", ""), f"REF {doc.sku or ''}"
    elif doc.doc_type is DocType.PCO:
        code, desc, raw = doc.header.get("pco_number", ""), f"PCO {doc.header.get('pco_number', '')} rev {doc.header.get('revision', '?')}", f"PCO {doc.header.get('pco_number', '')}"
    else:
        code, desc, raw = doc.header.get("drawing_number", "") or (doc.sku or ""), doc.header.get("title", ""), f"Drawing {doc.header.get('drawing_number', '')}"
    return DocumentItem(
        id=f"{doc.id}:header", doc_id=doc.id, doc_type=doc.doc_type, sku=doc.sku, item_number=code or None, description=desc or kind_desc,
        category=ItemCategory.ADMINISTRATIVE, category_reason="document header", attributes={"kind": "header"},
        evidence=Evidence(file=doc.path, file_sha256=doc.sha256, page=1 if doc.path.lower().endswith(".pdf") else None, raw_text=raw, locator="document header"),
    )

"""Check 2: BOM ↔ Packaging drawing — presence/identity only (the drawing is not a quantity source), plus a
drawing-number / revision row when the BOM references the drawing."""

import re

from kaizen.checks.base import RowIdFactory, header_item, pair_token
from kaizen.checks.bom_label import comparable_bom_items
from kaizen.checks.pairing import CheckPolicy, disc, run_pairing_check
from kaizen.matching.ladder import MatchLadder
from kaizen.models import CheckResult, CheckType, Classification, DiscrepancyType, Document, ItemCategory, MatchLevel, Severity, Thresholds

CHECK_VERSION = "1"
POLICY = CheckPolicy(check_type=CheckType.BOM_DRAWING, row_letter="D", quantity_relevant=False, missing_a=DiscrepancyType.MISSING_IN_DRAWING, missing_b=DiscrepancyType.EXTRA_ON_DRAWING, a_label="BOM component", b_label="drawing callout", conditional_b_exempt=True, soft_a_categories=(ItemCategory.PACKAGING,), exempt_b_categories=(ItemCategory.LABEL, ItemCategory.DOCUMENT))


def drawing_relevant_bom_items(bom: Document):
    """Physical components plus packaging lines (tray, lid): packaging is shown on a tray drawing but a BOM
    packaging line without a callout is not a finding (soft)."""
    physical = comparable_bom_items(bom)
    packaging = [i for i in bom.items if i.category is ItemCategory.PACKAGING and i.is_active and (i.quantity is None or i.quantity > 0)]
    return physical + packaging
_REV_RE = re.compile(r"\bREV\.?\s*([A-Z0-9]{1,3})\b", re.IGNORECASE)


def callouts(drawing: Document):
    return [i for i in drawing.items if i.attributes.get("kind") == "callout"]


def run_bom_drawing_check(bom: Document, drawing: Document, ladder: MatchLadder, thresholds: Thresholds) -> list[CheckResult]:
    sku = bom.sku or "UNKNOWN"
    ids = RowIdFactory(sku, "D", pair_token(bom.id, drawing.id))
    results = [_reference_row(bom, drawing, sku, ids)]
    results.extend(run_pairing_check(bom, drawing_relevant_bom_items(bom), drawing, callouts(drawing), POLICY, ladder, thresholds, sku, ids))
    return results


def _reference_row(bom: Document, drawing: Document, sku: str, ids: RowIdFactory) -> CheckResult:
    number = (drawing.header.get("drawing_number") or "").upper()
    rev = str(drawing.header.get("revision") or "")
    a_hdr, b_hdr = header_item(bom, "BOM"), header_item(drawing, "drawing")
    ref_rows = [i for i in bom.items if number and number in i.description.upper()]
    if not number:
        detail = "drawing number could not be read from the title block; the drawing cannot be tied to the BOM"
        return CheckResult(row_id=ids.next(), sku=sku, check=CheckType.BOM_DRAWING, role="reference", source_a=a_hdr, source_b=b_hdr, classification=Classification.MISSING, match_level=MatchLevel.NONE, score=0.0, explanation=detail, discrepancies=[disc(DiscrepancyType.DRAWING_REV_MISMATCH, Severity.MAJOR, detail)], requires_validation=True)
    if not ref_rows:
        return CheckResult(row_id=ids.next(), sku=sku, check=CheckType.BOM_DRAWING, role="reference", source_a=a_hdr, source_b=b_hdr, normalized_a=None, normalized_b=f"{number} REV {rev}", classification=Classification.POTENTIAL, match_level=MatchLevel.NONE, score=0.0, explanation=f"drawing {number} rev {rev} ({drawing.header.get('title', '')}); no BOM line references this drawing number — confirm the drawing applies to {sku}", requires_validation=True)
    row = ref_rows[0]
    m = _REV_RE.search(row.description)
    bom_rev = m.group(1) if m else ""
    if bom_rev and rev and bom_rev.upper() != rev.upper():
        detail = f"BOM line {row.item_number} references {number} REV {bom_rev} but the drawing is REV {rev}"
        return CheckResult(row_id=ids.next(), sku=sku, check=CheckType.BOM_DRAWING, role="reference", source_a=row, source_b=b_hdr, normalized_a=f"{number} REV {bom_rev}", normalized_b=f"{number} REV {rev}", classification=Classification.MISMATCH, match_level=MatchLevel.NONE, score=0.0, explanation=detail, discrepancies=[disc(DiscrepancyType.DRAWING_REV_MISMATCH, Severity.MAJOR, detail)], requires_validation=True)
    rev_note = f"REV {rev}" if bom_rev else f"(BOM line does not state a revision; drawing is REV {rev})"
    return CheckResult(row_id=ids.next(), sku=sku, check=CheckType.BOM_DRAWING, role="reference", source_a=row, source_b=b_hdr, normalized_a=f"{number} REV {bom_rev}", normalized_b=f"{number} REV {rev}", classification=Classification.EXACT, match_level=MatchLevel.EXACT, score=1.0, explanation=f"BOM line {row.item_number} references drawing {number} {rev_note}", requires_validation=not bom_rev)

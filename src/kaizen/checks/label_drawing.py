"""Check 3: Label ↔ Packaging drawing — presence only, both sides without item numbers."""

from kaizen.checks.base import RowIdFactory, header_item, pair_token
from kaizen.checks.bom_drawing import callouts, extraction_blocker, reference_only_rows
from kaizen.checks.pairing import CheckPolicy, disc, run_pairing_check
from kaizen.matching.ladder import MatchLadder
from kaizen.models import CheckResult, CheckType, Classification, DiscrepancyType, Document, ItemCategory, MatchLevel, Severity, Thresholds

CHECK_VERSION = "4"
POLICY = CheckPolicy(check_type=CheckType.LABEL_DRAWING, row_letter="L", quantity_relevant=False, missing_a=DiscrepancyType.MISSING_IN_DRAWING, missing_b=DiscrepancyType.EXTRA_ON_DRAWING, a_label="label line", b_label="drawing callout", conditional_b_exempt=True, exempt_b_categories=(ItemCategory.PACKAGING, ItemCategory.LABEL, ItemCategory.DOCUMENT))


def run_label_drawing_check(label: Document, drawing: Document, ladder: MatchLadder, thresholds: Thresholds, sku: str | None = None, *, applicable: bool | None = None) -> list[CheckResult]:
    sku = sku or label.sku or "UNKNOWN"
    ids = RowIdFactory(sku, "L", pair_token(label.id, drawing.id))
    if applicable is False:
        detail = "The supplied drawing is not referenced by this SKU's BOM. Confirm the applicable released drawing before comparing label contents."
        return [CheckResult(row_id=ids.next(), sku=sku, check=CheckType.LABEL_DRAWING, role="reference",
                source_a=header_item(label, "label"), source_b=header_item(drawing, "drawing"), classification=Classification.POTENTIAL,
                match_level=MatchLevel.NONE, explanation=detail,
                discrepancies=[disc(DiscrepancyType.DRAWING_APPLICABILITY_UNCONFIRMED, Severity.MAJOR, detail)], requires_validation=True)]
    if not label.items or label.header.get("unreadable_pages"):
        return [extraction_blocker(label, CheckType.LABEL_DRAWING, sku, ids)]
    if not callouts(drawing) or drawing.header.get("unreadable_pages"):
        return [extraction_blocker(drawing, CheckType.LABEL_DRAWING, sku, ids)]
    return reference_only_rows(run_pairing_check(label, list(label.items), drawing, callouts(drawing), POLICY, ladder, thresholds, sku, ids), drawing)

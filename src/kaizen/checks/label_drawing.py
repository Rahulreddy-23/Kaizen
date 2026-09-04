"""Check 3: Label ↔ Packaging drawing — presence only, both sides without item numbers."""

from kaizen.checks.base import RowIdFactory, pair_token
from kaizen.checks.bom_drawing import callouts
from kaizen.checks.pairing import CheckPolicy, run_pairing_check
from kaizen.matching.ladder import MatchLadder
from kaizen.models import CheckResult, CheckType, DiscrepancyType, Document, ItemCategory, Thresholds

CHECK_VERSION = "1"
POLICY = CheckPolicy(check_type=CheckType.LABEL_DRAWING, row_letter="L", quantity_relevant=False, missing_a=DiscrepancyType.MISSING_IN_DRAWING, missing_b=DiscrepancyType.EXTRA_ON_DRAWING, a_label="label line", b_label="drawing callout", conditional_b_exempt=True, exempt_b_categories=(ItemCategory.PACKAGING, ItemCategory.LABEL, ItemCategory.DOCUMENT))


def run_label_drawing_check(label: Document, drawing: Document, ladder: MatchLadder, thresholds: Thresholds, sku: str | None = None) -> list[CheckResult]:
    sku = sku or label.sku or "UNKNOWN"
    return run_pairing_check(label, list(label.items), drawing, callouts(drawing), POLICY, ladder, thresholds, sku, RowIdFactory(sku, "L", pair_token(label.id, drawing.id)))

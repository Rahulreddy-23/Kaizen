from decimal import Decimal

import pytest

from kaizen.ingest.bom_categorize import categorize, load_rules
from kaizen.models import ItemCategory


@pytest.mark.parametrize(
    "item_number, description, qty, expected",
    [
        ("0396447", "ABSORBENT TOWEL", "1.0000", ItemCategory.PHYSICAL_COMPONENT),
        ("5167473", "TAPE ANCHOR PER-Q-CATH", "1.0000", ItemCategory.PHYSICAL_COMPONENT),
        ("BAW0722153", "EN LOD, CASE LABEL", "0.4000", ItemCategory.LABEL),
        ("BAW0724416", "EN LOD, UNIT LABEL", "1.0000", ItemCategory.LABEL),
        ("C293054", "LABEL, PRIMING VOLUME, BLANK", "1.0000", ItemCategory.LABEL),
        ("PK0726442", "CASE LABEL, BLANK", "0.4000", ItemCategory.LABEL),
        ("PK0736411", "PORT ACCESS KIT LABEL STOCK", "1.0000", ItemCategory.LABEL),
        ("MPS0090", "PRODUCING LABELS ON THE", "0.0000", ItemCategory.PROCESS),
        ("MPS0019", "PACKAGING QUALITY", "0.0000", ItemCategory.QUALITY),
        ("FM00182", "FIRST/LAST LABEL RECORD", "0.0000", ItemCategory.QUALITY),
        ("0703450", "LOD THERMAL TRANSFER RIBBON", "0.0000", ItemCategory.PROCESS),
        ("PK0744425", "IFU, CATH TRIMMING DEVICE", "1.0000", ItemCategory.DOCUMENT),
        ("PK0100001", "TRAY, THERMOFORMED", "1.0000", ItemCategory.PACKAGING),
        ("PK0100002", "CARTON, SHIPPER", "0.2500", ItemCategory.PACKAGING),
        ("9999999", "WIDGET UNDESCRIBED", "0.0000", ItemCategory.UNKNOWN),
    ],
)
def test_category(item_number, description, qty, expected):
    category, reason = categorize(item_number, description, Decimal(qty))
    assert category is expected, reason


def test_reason_is_explanatory():
    _, reason = categorize("MPS0090", "PRODUCING LABELS ON THE", Decimal("0"))
    assert "PRODUCING" in reason or "MPS" in reason


def test_default_physical_reason_mentions_quantity():
    category, reason = categorize("1234567", "SOMETHING NEW", Decimal("2"))
    assert category is ItemCategory.PHYSICAL_COMPONENT
    assert "quantity" in reason.lower()


def test_rules_file_has_version():
    rules = load_rules()
    assert rules["version"]
    assert rules["keyword_rules"]


def test_unreadable_quantity_is_still_physical_so_it_is_reviewed():
    category, reason = categorize("2330001", "TOURNIQUET", None)
    assert category is ItemCategory.PHYSICAL_COMPONENT
    assert "unreadable" in reason

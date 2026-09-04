from decimal import Decimal

from kaizen.checks.quantity_compare import compare_quantities
from kaizen.models import SubQuantity


def test_equal_quantities():
    v = compare_quantities(Decimal("1.0000"), Decimal("1"))
    assert v.equal is True and v.explainable_by_idiom is False


def test_plain_mismatch():
    v = compare_quantities(Decimal("2.0000"), Decimal("1"))
    assert v.equal is False and v.explainable_by_idiom is False
    assert "2" in v.detail and "1" in v.detail


def test_per_idiom_explains_difference():
    v = compare_quantities(Decimal("6"), Decimal("2"), sub=SubQuantity(value=3, kind="per", raw="(3 per)"))
    assert v.equal is False and v.explainable_by_idiom is True
    assert "3 per" in v.detail


def test_pair_idiom_explains_difference():
    v = compare_quantities(Decimal("2"), Decimal("1"), sub=SubQuantity(value=1, kind="pair", raw="(1 pair)"))
    assert v.explainable_by_idiom is True


def test_pair_uom_explains_difference():
    v = compare_quantities(Decimal("2"), Decimal("1"), label_uom="PAIR")
    assert v.explainable_by_idiom is True


def test_idiom_that_does_not_reconcile_is_plain_mismatch():
    v = compare_quantities(Decimal("5"), Decimal("2"), sub=SubQuantity(value=3, kind="per", raw="(3 per)"))
    assert v.equal is False and v.explainable_by_idiom is False


def test_missing_quantity():
    v = compare_quantities(None, Decimal("1"))
    assert v.equal is False and "missing" in v.detail.lower()

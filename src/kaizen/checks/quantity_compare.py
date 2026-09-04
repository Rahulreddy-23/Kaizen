"""Quantity comparison that understands label idioms such as '(3 per)' and '(1 pair)'."""

from dataclasses import dataclass
from decimal import Decimal

from kaizen.models import SubQuantity


@dataclass(frozen=True)
class QtyVerdict:
    equal: bool
    explainable_by_idiom: bool
    detail: str


def _fmt(q: Decimal | None) -> str:
    if q is None:
        return "?"
    return format(q.normalize(), "f")


def compare_quantities(
    bom_qty: Decimal | None,
    label_qty: Decimal | None,
    sub: SubQuantity | None = None,
    bom_uom: str | None = None,
    label_uom: str | None = None,
) -> QtyVerdict:
    if bom_qty is None or label_qty is None:
        side = "BOM" if bom_qty is None else "label"
        return QtyVerdict(False, False, f"quantity missing on the {side} side (BOM {_fmt(bom_qty)} vs label {_fmt(label_qty)})")
    if bom_qty == label_qty:
        return QtyVerdict(True, False, f"BOM {_fmt(bom_qty)} == label {_fmt(label_qty)}")
    base = f"BOM {_fmt(bom_qty)} vs label {_fmt(label_qty)}"
    if sub is not None:
        multiplier = 2 if sub.kind == "pair" else sub.value
        if label_qty * multiplier == bom_qty:
            return QtyVerdict(False, True, f"{base}; reconciles if '{sub.raw}' is counted: {_fmt(label_qty)} x {multiplier} = {_fmt(bom_qty)} (reviewer to confirm)")
    if label_uom and label_uom.upper() == "PAIR" and label_qty * 2 == bom_qty:
        return QtyVerdict(False, True, f"{base}; reconciles if a pair counts as 2 each (reviewer to confirm)")
    return QtyVerdict(False, False, base)

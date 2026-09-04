from decimal import Decimal

import pytest

from kaizen.ingest.quantity import parse_label_line


@pytest.mark.parametrize(
    "line, qty, uom, desc",
    [
        ("1 Each - Towel, Absorbent", Decimal("1"), "EACH", "Towel, Absorbent"),
        ("10 Each - Gauze, 10 cm x 10 cm (4 in. x 4 in.)", Decimal("10"), "EACH", "Gauze, 10 cm x 10 cm (4 in. x 4 in.)"),
        ("2 Each – Blue Elastic Band", Decimal("2"), "EACH", "Blue Elastic Band"),
        ("1 EA - Mask", Decimal("1"), "EACH", "Mask"),
        ("6 Each -  Gauze, 5 cm x 5 cm (2 in. x 2 in.)", Decimal("6"), "EACH", "Gauze, 5 cm x 5 cm (2 in. x 2 in.)"),
    ],
)
def test_basic_quantity_line(line, qty, uom, desc):
    parsed = parse_label_line(line)
    assert parsed.matched is True
    assert parsed.quantity == qty
    assert parsed.uom == uom
    assert parsed.description == desc
    assert parsed.sub_quantity is None


def test_parenthetical_per_is_sub_quantity_and_removed_from_description():
    parsed = parse_label_line("2 Each - Tape Strips (3 per)")
    assert parsed.quantity == Decimal("2")
    assert parsed.description == "Tape Strips"
    assert parsed.sub_quantity is not None
    assert parsed.sub_quantity.value == 3
    assert parsed.sub_quantity.kind == "per"
    assert parsed.sub_quantity.raw == "(3 per)"


def test_parenthetical_pair_is_sub_quantity():
    parsed = parse_label_line("1 Each - Gloves (1 pair)")
    assert parsed.description == "Gloves"
    assert parsed.sub_quantity.value == 1
    assert parsed.sub_quantity.kind == "pair"


def test_dimension_parenthetical_is_not_a_sub_quantity():
    parsed = parse_label_line("10 Each - Gauze, 10 cm x 10 cm (4 in. x 4 in.)")
    assert parsed.sub_quantity is None


def test_non_quantity_line_does_not_match():
    parsed = parse_label_line("Store between 20°C - 25°C (68°F - 77°F).")
    assert parsed.matched is False
    assert parsed.quantity is None
    assert parsed.description == "Store between 20°C - 25°C (68°F - 77°F)."


def test_per_pouch_idiom():
    parsed = parse_label_line("1 Each - ECG Electrodes, 3 per pouch")
    assert parsed.quantity == Decimal("1")
    assert parsed.sub_quantity.value == 3
    assert parsed.sub_quantity.kind == "per"
    assert parsed.description == "ECG Electrodes"

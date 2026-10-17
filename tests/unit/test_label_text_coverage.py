"""Keep valid contents and the source text that is outside component comparisons."""

from decimal import Decimal

import pymupdf
import pytest

from kaizen.ingest.label_pdf import parse_label_pdf
from kaizen.ingest.quantity import parse_label_line
from kaizen.models import Document


def page(pdf, lines):
    p = pdf.new_page(width=420, height=300)
    for n, text in enumerate(lines):
        p.insert_text((20, 30 + 16 * n), text, fontsize=8)


def test_continuation_without_a_repeated_contents_heading_is_not_lost(tmp_path):
    path = tmp_path / 'label.pdf'
    with pymupdf.open() as pdf:
        page(pdf, ['REF 4567890', 'Example Kit', 'Contents:', '1 Each - Cap'])
        page(pdf, ['2 Each - Sponge', 'Store between 10 and 20 C'])
        pdf.save(path)
    doc = parse_label_pdf(path)
    assert [(i.description, int(i.quantity), i.evidence.page) for i in doc.items] == [('Cap', 1, 1), ('Sponge', 2, 2)]
    assert any('Store between' in i.description for i in doc.text_lines)
    assert not any('Store between' in i.description for i in doc.items)
    assert all(i.evidence.page and i.evidence.bbox for i in doc.text_lines)


def test_a_ref_below_the_contents_does_not_erase_the_product_name(tmp_path):
    path = tmp_path / 'label.pdf'
    with pymupdf.open() as pdf:
        page(pdf, ['Example Product Kit', 'Contents:', '1 Each - Cap', 'REF 4567890'])
        pdf.save(path)
    doc = parse_label_pdf(path)
    assert doc.header['product_name'] == 'Example Product Kit'
    assert doc.sku == '4567890' and len(doc.items) == 1
    loaded = Document.model_validate_json(doc.model_dump_json())
    assert loaded.text_lines == doc.text_lines


@pytest.mark.parametrize('text,qty,description', [('2 Each Sponge', 2, 'Sponge'), ('1,000 EA Fasteners', 1000, 'Fasteners'), ('3 Pair Gloves', 3, 'Gloves')])
def test_explicit_units_keep_contents_when_a_dash_is_absent(text, qty, description):
    parsed = parse_label_line(text)
    assert parsed.matched and parsed.quantity == Decimal(qty) and parsed.description == description


@pytest.mark.parametrize('text', ['20 G introducer', '10 cm bandage', '25 Store between 10 and 20', '1 Each'])
def test_dimensions_and_incomplete_starters_are_not_contents(text):
    assert not parse_label_line(text).matched


def test_thousands_quantity_is_a_new_entry_rather_than_a_continuation(tmp_path):
    path = tmp_path / 'label.pdf'
    with pymupdf.open() as pdf:
        page(pdf, ['REF 4567890', 'Example Kit', 'Contents:', '1 Each - Tray', '1,000 EA Fasteners'])
        pdf.save(path)
    doc = parse_label_pdf(path)
    assert [(i.description, int(i.quantity)) for i in doc.items] == [('Tray', 1), ('Fasteners', 1000)]


@pytest.mark.parametrize('ocr_text,native,expected', [
    ('2Each-Syringe,5mL', '2 Each - Syringe, 5 mL', '2 Each - Syringe, 5 mL'),
    ('CatheterwithGuide,21G', 'Catheter with Guide, 21 G', 'Catheter with Guide, 21 G'),
    ('NEWCODE1234 2Each', 'NEWCODE9999 2 Each', 'NEWCODE1234 2Each'),
])
def test_native_spacing_never_replaces_ocr_characters_or_identifiers(ocr_text, native, expected):
    from kaizen.ingest.text_lines import restore_supported_spacing
    result = restore_supported_spacing(ocr_text, native)
    assert result == expected
    assert ''.join(result.split()) == ''.join(ocr_text.split())

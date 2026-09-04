from decimal import Decimal

import pytest

from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.ingest.label_pdf import PARSER_NAME, parse_label_pdf
from kaizen.models import DocType, ItemCategory

BRIEF_CONTENTS = [
    "1 Each - Dual-Lumen PICC, 5.0 F (1.81 mm OD) x 55 cm, with Sherlock 3CG™ TPS Stylet/T-Lock Assembly and Stylet Funnel",
    "1 Each - Towel, Absorbent",
    "1 Each - Surgical Tape",
    "1 Each - Syringe, 5 mL",
    "1 Each - StatLock™ Stabilization Device",
    "1 Each - Introducer, Safety Peripheral IV Catheter, 20 G (1.1 mm OD x 45 mm Length)",
    "1 Each - ChloraPrep™ Solution One-Step Applicator, 3 mL",
    "1 Each - Aspiration Device",
    "2 Each - Tape Strips (3 per)",
    "10 Each - Gauze, 10 cm x 10 cm (4 in. x 4 in.)",
    "6 Each - Gauze, 5 cm x 5 cm (2 in. x 2 in.)",
    "2 Each - Measuring Tape",
    "2 Each - Mask",
    "1 Each - Adhesive Dressing",
    "2 Each - End Cap",
    "1 Each - Wipe, 70% Isopropyl Alcohol",
    "1 Each - ECG Leads Assembly",
    "1 Each - ECG Electrodes, 3 per pouch",
    "1 Each - Gloves (1 pair)",
    "2 Each - Blue Elastic Band",
    "1 Each - Remote Control Holder",
    "1 Each - Tourniquet",
    "1 Each - Catheter Trimming Device",
    "1 Each - Needle, Introducer, 21 G (0.9 mm OD x 0.55 mm ID x 70 mm Length)",
    "1 Each - Drape, Absorbent",
    "1 Each - Drape, Fenestrated",
    "1 Each - Needle, Safety Hypodermic, 25 G (0.5 mm OD x 16 mm Length)",
    "1 Each - Safety Scalpel",
    "1 Each - MicroEZ™ Microintroducer, 5.0 F (1.8 mm ID x 2.5 mm OD x 7 cm Length) with Vessel Dilator (0.5 mm ID)",
    "1 Each - Sherlock™ Sensor Holder",
    "1 Each - Flexura™ Guidewire, Nitinol with Straight Tip, 0.46 mm (0.018 in.) OD x 50 cm, Bendable",
    "1 Each - Lidocaine HCl 1%, 5 mL ampule",
    "2 Each - Syringe, Sodium Chloride (Saline) 0.9%, 10 mL",
]
PRODUCT_NAME = "PowerPICC SOLO2 Catheter with Sherlock 3CG Tip Positioning System (TPS) Stylet"


@pytest.fixture
def brief_label(tmp_path):
    spec = LabelSpec(ref="1295108", product_name=PRODUCT_NAME, contents=BRIEF_CONTENTS)
    return render_label_pdf(spec, tmp_path / "label.pdf")


def test_ref_and_product_name(brief_label):
    doc = parse_label_pdf(brief_label)
    assert doc.doc_type is DocType.LABEL
    assert doc.parser_name == PARSER_NAME
    assert doc.sku == "1295108"
    assert doc.header["ref"] == "1295108"
    assert doc.header["ref_occurrences"] >= 5
    assert doc.header["product_name"] == PRODUCT_NAME


def test_all_content_lines_recovered_in_reading_order_without_interleaving(brief_label):
    doc = parse_label_pdf(brief_label)
    expected = [c.split(" - ", 1)[1] for c in BRIEF_CONTENTS]
    # sub-quantity idioms are removed from the description by design
    expected = [e.replace(" (3 per)", "").replace(" (1 pair)", "").replace(", 3 per pouch", "") for e in expected]
    got = [i.description for i in doc.items]
    assert got == expected


def test_wrapped_line_is_one_item_with_full_description(brief_label):
    doc = parse_label_pdf(brief_label)
    picc = doc.items[0]
    assert picc.description.startswith("Dual-Lumen PICC, 5.0 F")
    assert picc.description.endswith("Stylet Funnel")
    assert picc.attributes["line_count"] >= 2
    assert picc.evidence.bbox is not None
    assert picc.evidence.page == 1


def test_quantities_and_sub_quantities(brief_label):
    doc = parse_label_pdf(brief_label)
    by_desc = {i.description: i for i in doc.items}
    assert by_desc["Gauze, 10 cm x 10 cm (4 in. x 4 in.)"].quantity == Decimal("10")
    assert by_desc["Tape Strips"].quantity == Decimal("2")
    assert by_desc["Tape Strips"].sub_quantity.value == 3
    assert by_desc["Gloves"].sub_quantity.kind == "pair"
    assert by_desc["ECG Electrodes"].sub_quantity.value == 3
    assert all(i.uom == "EACH" for i in doc.items)
    assert all(i.category is ItemCategory.PHYSICAL_COMPONENT for i in doc.items)
    assert all(i.sku == "1295108" for i in doc.items)


def test_peel_off_and_footer_text_are_not_items(brief_label):
    doc = parse_label_pdf(brief_label)
    descriptions = " | ".join(i.description for i in doc.items)
    assert "LOT" not in descriptions
    assert "trademark" not in descriptions.lower()
    assert "Assembled" not in descriptions
    assert len(doc.items) == len(BRIEF_CONTENTS)


def test_single_column_label(tmp_path):
    spec = LabelSpec(ref="2231234", product_name="Simple Kit", contents=["1 Each - Towel, Absorbent", "2 Each - Mask"], columns=1)
    doc = parse_label_pdf(render_label_pdf(spec, tmp_path / "l.pdf"))
    assert [i.description for i in doc.items] == ["Towel, Absorbent", "Mask"]
    assert doc.sku == "2231234"


def test_label_without_contents_anchor_warns(tmp_path):
    spec = LabelSpec(ref="2231234", product_name="Simple Kit", contents=[], contents_heading=None)
    doc = parse_label_pdf(render_label_pdf(spec, tmp_path / "l.pdf"))
    assert doc.items == []
    assert any("contents" in w.lower() for w in doc.warnings)

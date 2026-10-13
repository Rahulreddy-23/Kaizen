"""Guard conservative OCR recovery, evidence and bilingual drawing metadata."""

from decimal import Decimal

import pymupdf
import pytest

from kaizen.checks.bom_drawing import callouts
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.ingest import ocr
from kaizen.ingest.drawing_pdf import parse_drawing_pdf
from kaizen.ingest.label_pdf import parse_label_pdf
from kaizen.ingest.ocr import OcrResult, correct_fused_label_words


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("SafetyPeripheralIVCatheter", "Safety Peripheral IV Catheter"),
        ("NitinolwithStraightTip", "Nitinol with Straight Tip"),
        ("SAFETYPERIPHERALIVCATHETER", "SAFETY PERIPHERAL IV CATHETER"),
        ("1 Each - NitinolwithStraightTip, 10 CM", "1 Each - Nitinol with Straight Tip, 10 CM"),
        ("Microintroducer Guidewire", "Microintroducer Guidewire"),
        ("SafetyPeripheralIVCatheter123", "SafetyPeripheralIVCatheter123"),
        ("123SafetyPeripheralIVCatheter", "123SafetyPeripheralIVCatheter"),
        ("UnknownSafetyPeripheralIVCatheter", "UnknownSafetyPeripheralIVCatheter"),
        ("SafetyPeripheralIVCatheter_ABC", "SafetyPeripheralIVCatheter_ABC"),
    ],
)
def test_fused_label_recovery_is_conservative(raw, expected):
    assert correct_fused_label_words(raw) == expected
    assert correct_fused_label_words(expected) == expected


def test_ambiguous_label_segmentation_is_preserved(monkeypatch):
    # Both GUIDE WIRE HOLDER and GUIDEWIRE HOLDER become possible if WIRE is approved.
    monkeypatch.setattr(ocr, "_LABEL_WORDS", ocr._LABEL_WORDS | {"WIRE"})
    assert correct_fused_label_words("GuideWireHolder") == "GuideWireHolder"


def test_long_ocr_join_does_not_exhaust_the_call_stack():
    assert correct_fused_label_words("IV" * 1500) == " ".join(["IV"] * 1500)
    unknown = "IV" * 1500 + "Unknown"
    assert correct_fused_label_words(unknown) == unknown


def _page(path, lines, *, scan=False):
    """Use deterministic recognized words, so these regressions need no OCR engine."""
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=792, height=612)
        for y, text in lines:
            page.insert_text((40, y), text, fontsize=7)
        words = page.get_text("words")
        if scan:
            pix = page.get_pixmap(dpi=72)
            with pymupdf.open() as image_pdf:
                image_page = image_pdf.new_page(width=792, height=612)
                image_page.insert_image(image_page.rect, pixmap=pix)
                image_pdf.save(path)
        else:
            pdf.save(path)
    return words


def _mock_ocr(monkeypatch, parser, words):
    # An unrelated low-confidence word must not lower REF or entry confidence.
    result = OcrResult(words=[(*w[:5], 0.1 if w[4] == "Kit" else 0.88) for w in words], engine="fake-ocr", dpi=240)
    monkeypatch.setattr(f"kaizen.ingest.{parser}.ocr_available", lambda: True)
    monkeypatch.setattr(f"kaizen.ingest.{parser}.ocr_page", lambda page: result)


def test_ocr_label_recovery_preserves_raw_evidence_and_field_confidence(tmp_path, monkeypatch):
    path = tmp_path / "label.pdf"
    words = _page(path, [(30, "REF 1295108"), (50, "Kit"), (70, "Contents:"), (90, "2 Each - SafetyPeripheralIVCatheter")], scan=True)
    _mock_ocr(monkeypatch, "label_pdf", words)
    label = parse_label_pdf(path)
    item, = label.items
    assert item.description == "Safety Peripheral IV Catheter"
    assert item.quantity == Decimal(2) and item.uom == "EACH"
    assert item.evidence.raw_text == item.attributes["raw_line"] == "2 Each - SafetyPeripheralIVCatheter"
    assert item.attributes["ocr_corrected_line"] == "2 Each - Safety Peripheral IV Catheter"
    assert item.evidence.extraction_method == "ocr" and item.evidence.bbox is not None
    assert label.header["identity_confidence"] == item.extraction_confidence == 0.88
    assert any("fake-ocr, 240 dpi" in w and "produced" in w for w in label.warnings)
    assert not any("min confidence" in w for w in label.warnings)


def test_fused_native_label_description_is_preserved(tmp_path):
    path = render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - SafetyPeripheralIVCatheter"]), tmp_path / "label.pdf")
    item, = parse_label_pdf(path).items
    assert item.description == "SafetyPeripheralIVCatheter"
    assert item.attributes["ocr_corrected_line"] is None


@pytest.mark.parametrize("scan", [False, True])
@pytest.mark.parametrize("en,es,placement", [
    ("MASK PLACED ON THE TRAY (2)", "MASCARILLA COLOCADA SOBRE LA BANDEJA", "PLACED ON THE TRAY"),
    ("MASK PLACED ON TRAY (2)", "MASCARILLA COLOCADO SOBRE LA BANDEJA", "PLACED ON TRAY"),
    ("MASK PLACED ON TRAY (2)", "MASCARILLA", None),
])
def test_tray_placement_requires_bilingual_support(tmp_path, monkeypatch, scan, en, es, placement):
    path = tmp_path / "drawing.pdf"
    words = _page(path, [(80, en), (90, es)], scan=scan)
    if scan:
        _mock_ocr(monkeypatch, "drawing_pdf", words)
    drawing = parse_drawing_pdf(path)
    item, = callouts(drawing)
    assert item.description == ("MASK" if placement else "MASK PLACED ON TRAY")
    assert item.attributes["placement"] == placement
    assert item.attributes["depicted_count"] == "2" and item.quantity is None
    assert item.attributes["es_text"] == es
    assert item.evidence.raw_text == f"{en} / {es}"


@pytest.mark.parametrize("scan", [False, True])
@pytest.mark.parametrize("es", ["INSERTO AVISO ETIQUETADO ELECTRONICO", "INSERTO AVISO ELECTRONICO"])
def test_labeling_typo_is_corrected_only_in_ocr_with_spanish_support(tmp_path, monkeypatch, scan, es):
    path = tmp_path / "drawing.pdf"
    en = "ELECTRONIC LEBELING NOTICE INSERT"
    words = _page(path, [(80, en), (90, es), (140, "MASK"), (150, "MASCARILLA")], scan=scan)
    if scan:
        _mock_ocr(monkeypatch, "drawing_pdf", words)
    drawing = parse_drawing_pdf(path)
    notice = next(i for i in drawing.items if "ELECTRONIC" in i.description)
    corrected = scan and "ETIQUETADO" in es
    assert notice.description == ("ELECTRONIC LABELING NOTICE INSERT" if corrected else en)
    assert notice.attributes["kind"] == ("instruction" if corrected else "callout")
    assert notice.evidence.raw_text == f"{en} / {es}"
    assert "MASK" in [i.description for i in callouts(drawing)]


def test_labeling_notice_instruction_stays_visible_outside_component_checks(tmp_path):
    path = tmp_path / "drawing.pdf"
    _page(path, [(80, "ELECTRONIC LABELING NOTICE INSERT"), (90, "INSERTO AVISO ETIQUETADO ELECTRONICO"), (140, "MASK"), (150, "MASCARILLA")])
    drawing = parse_drawing_pdf(path)
    assert len(drawing.items) == 2
    assert [i.description for i in callouts(drawing)] == ["MASK"]

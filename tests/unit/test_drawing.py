import pymupdf
import pytest

from kaizen.datasets.drawing_docs import CalloutSpec, DrawingSpec, render_drawing_pdf
from kaizen.ingest.detect import detect_doc_type, parse_document
from kaizen.ingest.drawing_pdf import PARSER_NAME, is_spanish_line, parse_drawing_pdf
from kaizen.models import DocType, ItemCategory

CALLOUTS = [
    CalloutSpec("FORCEPS WITH PROTECTIVE TUBING", "FORCEPS CON TUBO PROTECTOR"),
    CalloutSpec("INTRODUCER NEEDLE", "AGUJA INTRODUCTORA"),
    CalloutSpec("EXCALIBUR", "EXCALIBUR"),
    CalloutSpec("MICROINTRODUCER", "MICROINTRODUCTOR"),
    CalloutSpec("SCALPEL", "ESCALPELO"),
    CalloutSpec("END CAPS", "TAPAS DE EXTREMO"),
    CalloutSpec("SCISSORS WITH PROTECTIVE TUBE OR CATHETER TRIMMING DEVICE", "TIJERAS CON TUBO PROTECTOR O DISPOSITIVO DE CORTE DEL CATETER", conditional=True, placement="PLACE IN EITHER CAVITY #2 OR #3 OR #5"),
    CalloutSpec("PROTECTIVE TUBE", "TUBO PROTECTOR"),
    CalloutSpec("GUIDE WIRE", "ALAMBRE GUIA"),
    CalloutSpec("SYRINGE LABEL", "ETIQUETA DE LA JERINGA"),
    CalloutSpec("TRAY", "BANDEJA"),
    CalloutSpec("TAPE MEASURE", "CINTA METRICA"),
    CalloutSpec("SYRINGES", "JERINGAS"),
    CalloutSpec("SHARP HOLDER", "PORTA NAVAJA", conditional=True),
    CalloutSpec("FILTER STRAW", "PAJILLA DE FILTRO"),
    CalloutSpec("SAFETY NEEDLE", "AGUJA DE SEGURIDAD"),
    CalloutSpec("CATHETER INSIDE TUBE", "CATETER DENTRO DEL TUBO"),
]


@pytest.fixture
def drawing(tmp_path):
    spec = DrawingSpec(drawing_number="DWG3173108", revision="11", title="FULL SINGLE TRAY ASSEMBLY", plant="REYNOSA, MEXICO", callouts=CALLOUTS, cavities=["2", "3", "5"], checked_by="Prasanth Kannan")
    return render_drawing_pdf(spec, tmp_path / "drawing.pdf")


def test_render_and_detect(drawing):
    text = pymupdf.open(drawing)[0].get_text()
    assert "DRAWING NO" in text and "DWG3173108" in text and "DO NOT SCALE PRINT" in text
    assert "CAVITY #2" in text and "CAVIDAD #2" in text
    assert detect_doc_type(drawing) is DocType.DRAWING
    assert parse_document(drawing).document.doc_type is DocType.DRAWING


def test_title_block(drawing):
    doc = parse_drawing_pdf(drawing)
    assert doc.parser_name == PARSER_NAME
    assert doc.header["drawing_number"] == "DWG3173108"
    assert doc.header["revision"] == "11"
    assert doc.header["title"] == "FULL SINGLE TRAY ASSEMBLY"
    assert doc.header["plant"] == "REYNOSA, MEXICO"
    assert doc.sku == "DWG3173108"


def test_callouts_extracted_english_only_with_spanish_kept_as_attribute(drawing):
    doc = parse_drawing_pdf(drawing)
    callouts = [i for i in doc.items if i.attributes.get("kind") == "callout"]
    got = [c.description for c in callouts]
    expected = [c.en for c in CALLOUTS]
    assert sorted(got) == sorted(expected), set(expected) ^ set(got)
    by_desc = {c.description: c for c in callouts}
    assert by_desc["FORCEPS WITH PROTECTIVE TUBING"].attributes["es_text"] == "FORCEPS CON TUBO PROTECTOR"
    assert all(c.category is ItemCategory.PHYSICAL_COMPONENT for c in callouts)
    assert all(c.quantity is None for c in callouts)  # a drawing is not a quantity source
    assert all(c.evidence.page == 1 and c.evidence.bbox is not None for c in callouts)


def test_conditional_and_placement_notes(drawing):
    doc = parse_drawing_pdf(drawing)
    by_desc = {i.description: i for i in doc.items if i.attributes.get("kind") == "callout"}
    sharp = by_desc["SHARP HOLDER"]
    assert sharp.attributes["conditional"] is True
    scissors = by_desc["SCISSORS WITH PROTECTIVE TUBE OR CATHETER TRIMMING DEVICE"]
    assert scissors.attributes["conditional"] is True
    assert "CAVITY" in scissors.attributes["placement"]
    assert by_desc["TRAY"].attributes["conditional"] is False


def test_noise_is_not_a_callout(drawing):
    doc = parse_drawing_pdf(drawing)
    descs = " | ".join(i.description for i in doc.items)
    for noise in ("CAVITY", "CAVIDAD", "NOTES", "TOLERANCES", "DO NOT SCALE", "Checked by", "THIRD ANGLE", "INCHES", "DRAWING NO"):
        assert noise not in descs, noise


@pytest.mark.parametrize("line, es", [("FORCEPS CON TUBO PROTECTOR", True), ("FORCEPS WITH PROTECTIVE TUBING", False), ("AGUJA DE SEGURIDAD", True), ("SAFETY NEEDLE", False), ("EXCALIBUR", False), ("CATÉTER DENTRO DEL TUBO", True), ("TAPAS DE EXTREMO", True), ("END CAPS", False)])
def test_spanish_detection(line, es):
    assert is_spanish_line(line) is es


def test_raster_only_drawing_warns(tmp_path):
    d = pymupdf.open()
    page = d.new_page(width=792, height=612)
    page.draw_rect(pymupdf.Rect(100, 100, 600, 400), width=1)
    path = tmp_path / "scan_drawing.pdf"
    d.save(path)
    doc = parse_drawing_pdf(path)
    assert doc.items == []
    assert any("no text" in w.lower() or "ocr" in w.lower() for w in doc.warnings)

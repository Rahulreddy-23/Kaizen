"""Recognize actual synthetic label/drawing pixels, independently of system Tesseract."""


import pymupdf
import pytest

from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.ingest import ocr
from kaizen.ingest.drawing_pdf import parse_drawing_pdf
from kaizen.ingest.label_pdf import parse_label_pdf


@pytest.fixture(autouse=True)
def portable_ocr(monkeypatch):
    # Test the engine installed by pip even on machines that also have Tesseract.
    # Missing/broken dependencies must fail this test, not skip it.
    ocr._rapid_module()
    monkeypatch.setattr(ocr, "available_engines", lambda: ["rapidocr-onnxruntime"])


def rasterize(source, target, rotation=0, native_footer=None):
    with pymupdf.open(source) as original, pymupdf.open() as pdf:
        for p in original:
            page = pdf.new_page(width=p.rect.width, height=p.rect.height)
            page.insert_image(page.rect, pixmap=p.get_pixmap(dpi=180))
            if native_footer:
                page.insert_text((20, page.rect.height - 12), native_footer, fontsize=8)
            page.set_rotation(rotation)
        pdf.save(target)
    return target


@pytest.mark.parametrize("layout", ["scan", "native-ref-only", "outlined"])
def test_portable_engine_reads_label_identity_quantities_and_source_boxes(tmp_path, layout):
    native = render_label_pdf(LabelSpec(ref="4567890", product_name="Example Kit", contents=["1 Each - Towel", "2 Each - Mask"], columns=1), tmp_path / "native.pdf")
    path = tmp_path / "label.pdf"
    if layout == "outlined":
        with pymupdf.open(native) as pdf:
            svg = pdf[0].get_svg_image(text_as_path=True)
        with pymupdf.open(stream=svg.encode(), filetype="svg") as pdf:
            path.write_bytes(pdf.convert_to_pdf())
        with pymupdf.open(path) as pdf:
            assert not pdf[0].get_images() and not pdf[0].get_text("words")
    else:
        rasterize(native, path, native_footer="REF 4567890" if layout == "native-ref-only" else None)
    doc = parse_label_pdf(path)
    assert doc.sku == "4567890"
    assert [(i.description, int(i.quantity)) for i in doc.items] == [("Towel", 1), ("Mask", 2)]
    assert not doc.header["unreadable_pages"]
    assert all(i.evidence.extraction_method == "ocr" and i.evidence.page == 1 and i.evidence.bbox for i in doc.items)


@pytest.mark.parametrize("native_footer", [None, "DRAWING NO DWG7654321"])
def test_portable_engine_reads_raster_callouts_even_with_a_native_title_block(tmp_path, native_footer):
    native, path = tmp_path / "native.pdf", tmp_path / "drawing.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=792, height=612)
        for y, text in [(80, "SURGICAL TAPE"), (100, "CINTA QUIRURGICA"), (180, "MASK"), (200, "MASCARILLA"), (560, "DRAWING NO DWG7654321")]:
            page.insert_text((80, y), text, fontsize=12)
        pdf.save(native)
    rasterize(native, path, native_footer=native_footer)
    doc = parse_drawing_pdf(path)
    assert doc.header["drawing_number"] == "DWG7654321"
    assert {i.description for i in doc.items} == {"SURGICAL TAPE", "MASK"}
    assert not doc.header["unreadable_pages"]
    assert all(i.evidence.extraction_method == "ocr" and i.evidence.bbox and i.quantity is None for i in doc.items)


def test_native_label_keeps_its_text_without_calling_ocr(tmp_path, monkeypatch):
    path = render_label_pdf(LabelSpec(ref="4567890", product_name="Example Kit", contents=["2 Each - Unfamiliar Part ABC"]), tmp_path / "label.pdf")

    def unexpected(*args, **kwargs):
        pytest.fail("A complete native label must not be re-read with OCR")

    monkeypatch.setattr("kaizen.ingest.label_pdf.ocr_page", unexpected)
    doc = parse_label_pdf(path)
    assert doc.items[0].description == "Unfamiliar Part ABC"
    assert doc.items[0].evidence.extraction_method == "pdf_text"


def test_portable_sessions_fit_a_single_core_without_changing_global_onnx_defaults(monkeypatch):
    import onnxruntime

    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    ocr._rapid_engine.cache_clear()
    engine = ocr._rapid_engine()
    for session in (engine.text_detector.infer.session, engine.text_recognizer.session.session, engine.text_cls.infer.session):
        options = session.get_session_options()
        assert options.intra_op_num_threads == options.inter_op_num_threads == 1
    assert onnxruntime.SessionOptions().intra_op_num_threads == 0
    ocr._rapid_engine.cache_clear()

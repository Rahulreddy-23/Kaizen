"""Real OCR recovery on outlined text, with altered synthetic codes and instructions."""

import pymupdf

from kaizen.ingest import ocr
from kaizen.ingest.drawing_pdf import _is_instruction, parse_drawing_pdf


def outline_pdf(native, target):
    with pymupdf.open(native) as pdf:
        svg = pdf[0].get_svg_image(text_as_path=True)
    with pymupdf.open(stream=svg.encode(), filetype='svg') as pdf:
        target.write_bytes(pdf.convert_to_pdf())


def test_missing_long_vector_notes_are_recovered_and_retained(tmp_path, monkeypatch):
    native, path = tmp_path / 'native.pdf', tmp_path / 'drawing.pdf'
    with pymupdf.open() as pdf:
        p = pdf.new_page(width=792, height=612)
        for y, text in [(80, 'PROTECTIVE COVER'), (95, 'CUBIERTA PROTECTORA'), (440, 'NOTES:'),
                        (455, '1. VERIFY THE INNER BARRIER BEFORE SHIPPING. KEEP THE ORIGINAL REVIEW REFERENCE.'),
                        (470, '2. INCLUDE ONE INFORMATION SHEET FOR EACH VARIANT LISTED IN THE APPROVED SPECIFICATION.'),
                        (560, 'DRAWING NO DWG7654321')]:
            p.insert_text((40, y), text, fontsize=8)
        pdf.save(native)
    outline_pdf(native, path)
    original = path.read_bytes()
    # Simulate a page detector missing the long notes entirely. The real crop
    # recognizer still has to read the pixels; no expected note text is injected.
    monkeypatch.setattr(ocr, 'available_engines', lambda: ['rapidocr-onnxruntime'])
    monkeypatch.setattr(ocr, '_recognize', lambda *args: [])
    ocr._CACHE.clear()
    doc = parse_drawing_pdf(path)
    all_text = ' '.join(i.description for i in doc.text_lines)
    assert 'VERIFY THE INNER BARRIER BEFORE SHIPPING' in all_text
    assert 'ONE INFORMATION SHEET FOR EACH VARIANT' in all_text
    assert 'APPROVED SPECIFICATION' in all_text
    assert doc.header['outline_rows_recovered'] > 0
    assert not any('INFORMATION SHEET' in i.description for i in doc.items)
    assert all(i.category.value == 'PROCESS' for i in doc.items if i.attributes.get('kind') == 'instruction')
    assert all(i.evidence.page == 1 and i.evidence.bbox for i in doc.text_lines)
    assert path.read_bytes() == original
    ocr._CACHE.clear()


def test_unknown_spanish_continuation_is_not_promoted_to_an_english_component(tmp_path):
    path = tmp_path / 'drawing.pdf'
    with pymupdf.open() as pdf:
        p = pdf.new_page(width=792, height=612)
        for y, text in [(80, 'PROTECTIVE COVER'), (90, 'CUBIERTA DE PROTECCION'), (100, 'NUEVO MODELO'), (150, 'UNFAMILIAR WIDGET')]:
            p.insert_text((40, y), text, fontsize=7)
        pdf.save(path)
    doc = parse_drawing_pdf(path)
    assert 'NUEVO MODELO' not in [i.description for i in doc.items]
    assert doc.items[0].attributes['es_text'].endswith('NUEVO MODELO')
    assert 'UNFAMILIAR WIDGET' in [i.description for i in doc.items]


def test_drafting_reference_does_not_make_an_instruction_a_component():
    assert _is_instruction('2 CORRECT PLACEMENT FOR ELECTRODE LEAD ASSEMBLY')
    assert _is_instruction('[14] STEP 2: CLOSE THE OUTER CARTON')
    assert not _is_instruction('2 WAY CONNECTOR')

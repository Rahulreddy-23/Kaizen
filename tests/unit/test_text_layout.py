"""Layout regressions use synthetic text and varied coordinates, never customer fixtures."""

import pymupdf
import pytest

from kaizen.ingest.drawing_pdf import parse_drawing_pdf
from kaizen.ingest.label_pdf import parse_label_pdf
from kaizen.ingest.pdf_words import Word
from kaizen.ingest.text_lines import capture_text_lines
from kaizen.models import DocType


def word(text, x0, y0, x1):
    return Word(text, x0, y0, x1, y0 + 8, 0, 0, 0, .93)


def capture(words, **kwargs):
    return capture_text_lines(words, doc_id='example', doc_type=DocType.LABEL, file='example.pdf', sha='a' * 64, page=1, method='ocr', **kwargs)


@pytest.mark.parametrize('count', [2, 3])
def test_columns_split_close_fragments_without_splitting_spanning_headers(count):
    words = [word('Full', 10, 10, 20), word('Kit', 28, 10, 38)]
    words += [word(f'{n}Each-Example', 10 + n * 50, 30, 55 + n * 50) for n in range(count)]
    lines = capture(words, column_cuts=tuple(8 + n * 50 for n in range(1, count)), column_y=(28, 40))
    assert [i.description for i in lines] == ['Full Kit', *[f'{n}Each-Example' for n in range(count)]]
    assert len({i.id for i in lines}) == len(lines)


def test_full_text_spacing_keeps_original_characters_boxes_and_evidence():
    source = [word('2Each-NewDeviceZX128', 10, 30, 130)]
    native = [word('2 Each - New Device ZX129', 10, 30, 130)]
    line = capture(source, reference_words=native)[0]
    assert line.description == '2 Each - New Device ZX128'
    assert line.evidence.raw_text == '2Each-NewDeviceZX128'
    assert ''.join(line.description.split()) == line.evidence.raw_text
    assert line.evidence.bbox.x0 == 10 and line.evidence.bbox.x1 == 130
    assert line.attributes['native_spacing_recovered']
    assert capture(source, reference_words=[word('Unrelated text', 10, 30, 130)])[0].description == source[0].text
    assert capture(source, reference_words=[word('2 Each New Device ZX128', 10, 60, 130)])[0].description == source[0].text


def test_label_full_text_uses_the_same_detected_columns_as_its_entries(tmp_path):
    path = tmp_path / 'label.pdf'
    with pymupdf.open() as pdf:
        p = pdf.new_page(width=420, height=300)
        for x, y, text in [(20, 30, 'REF 7654321'), (20, 45, 'Example Kit'), (20, 60, 'Contents:'),
                           (20, 80, '1 Each - Example component'), (125, 80, '2 Each - Other device'),
                           (20, 92, 'with protective sleeve'), (125, 92, 'with packaging'),
                           (20, 104, '3 Each - Tube'), (125, 104, '4 Each - Cover')]:
            p.insert_text((x, y), text, fontsize=7)
        pdf.save(path)
    doc = parse_label_pdf(path)
    assert len(doc.items) == 4
    assert len([i for i in doc.text_lines if i.evidence.bbox.y0 > 65]) == 6
    assert not any('component 2 Each' in i.description or 'sleeve with packaging' in i.description for i in doc.text_lines)


@pytest.mark.parametrize('offset', [0, 22])
def test_footer_notes_do_not_cut_off_a_neighbouring_bilingual_caption(tmp_path, offset):
    path = tmp_path / 'drawing.pdf'
    with pymupdf.open() as pdf:
        p = pdf.new_page(width=792, height=612)
        for x, y, text in [(470, 425, '*BOX NOTE: PLACE THE COVER ON THE LOWER SIDE'),
                           (482, 436, 'WITH THE SEAL FACING OUT.'),
                           (467, 447, '*NOTA DE LA CAJA: COLOCAR LA CUBIERTA'),
                           (482, 458, 'EN LA PARTE INFERIOR DE LA CAJA.'),
                           (20, 445, 'NOTES:'), (20, 460, '1. VERIFY THE PACKAGING.'),
                           (20, 480, 'NOTAS:'), (20, 495, '1. VERIFICAR EL EMBALAJE.'),
                           (410, 495, 'ANGLES +/- 1'), (410, 510, 'DWN'),
                           (470, 550, 'UNRELATED FOOTER'), (640, 570, 'DRAWING NO DWG7654321')]:
            p.insert_text((x, y + offset), text, fontsize=7)
        pdf.save(path)
    doc = parse_drawing_pdf(path)
    assert len(doc.items) == 1
    item = doc.items[0]
    assert item.attributes['kind'] == 'instruction'
    assert item.attributes['es_text'].endswith('EN LA PARTE INFERIOR DE LA CAJA.')
    assert 'EN LA PARTE INFERIOR' in item.evidence.raw_text
    notes = doc.header['notes'][0]['text']
    assert 'VERIFY THE PACKAGING' in notes and 'VERIFICAR EL EMBALAJE' in notes
    assert 'ANGLES' not in notes and 'DWN' not in notes
    assert 'UNRELATED FOOTER' not in ' '.join(i.description for i in doc.items)
    assert any('UNRELATED FOOTER' in i.description for i in doc.text_lines)


@pytest.mark.parametrize('suffix,condition', [
    ('(ES)', '(SI ES APLICABLE)'), ('(PVC)', '(CUANDO APLIQUE)'), ('(12 mm)', '(SI APLICA SEGUN EL BOM)'),
    ('(SI)', '(SI CORRESPONDE SEGUN EL BOM)'), ('(COLOCACION)', '(COLOCAR EN LA BANDEJA)'),
])
def test_meaningful_spanish_parentheses_are_preserved(tmp_path, suffix, condition):
    path = tmp_path / 'drawing.pdf'
    with pymupdf.open() as pdf:
        p = pdf.new_page()
        p.insert_text((40, 80), 'CONNECTOR (S)', fontsize=8)
        p.insert_text((40, 92), f'CONECTOR {suffix} {condition} (2)', fontsize=8)
        pdf.save(path)
    item = parse_drawing_pdf(path).items[0]
    assert item.attributes['es_text'] == f'CONECTOR {suffix}'
    assert condition in item.evidence.raw_text and '(2)' in item.evidence.raw_text

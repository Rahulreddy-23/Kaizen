"""Offline acceptance check: real synthetic scan pixels, never customer documents."""
import tempfile
from pathlib import Path

import pymupdf

from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.ingest.drawing_pdf import parse_drawing_pdf
from kaizen.ingest.label_pdf import parse_label_pdf
from kaizen.ingest.ocr import available_engines


def main():
    with tempfile.TemporaryDirectory(prefix='kaizen-ocr-check-') as folder:
        root = Path(folder)
        native = render_label_pdf(LabelSpec(ref='4567890', product_name='Example Kit', contents=['1 Each - Towel', '2 Each - Mask'], columns=1), root / 'native.pdf')
        with pymupdf.open(native) as source, pymupdf.open() as scan:
            page = scan.new_page(width=source[0].rect.width, height=source[0].rect.height)
            page.insert_image(page.rect, pixmap=source[0].get_pixmap(dpi=180))
            scan.save(root / 'label.pdf')
        label = parse_label_pdf(root / 'label.pdf')
        assert label.sku == '4567890', 'Label REF was not recovered'
        assert [(i.description, int(i.quantity)) for i in label.items] == [('Towel', 1), ('Mask', 2)], 'Label contents/quantities were not recovered'
        with pymupdf.open() as source, pymupdf.open() as scan:
            page = source.new_page(width=792, height=612)
            for y, text in [(80, 'SURGICAL TAPE'), (100, 'CINTA QUIRURGICA'), (180, 'MASK'), (200, 'MASCARILLA'), (560, 'DRAWING NO DWG7654321')]:
                page.insert_text((80, y), text, fontsize=12)
            target = scan.new_page(width=792, height=612)
            target.insert_image(target.rect, pixmap=page.get_pixmap(dpi=180))
            scan.save(root / 'drawing.pdf')
        drawing = parse_drawing_pdf(root / 'drawing.pdf')
        assert drawing.sku == 'DWG7654321', 'Drawing number was not recovered'
        assert {i.description for i in drawing.items} == {'SURGICAL TAPE', 'MASK'}, 'Drawing callouts were not recovered'
        for doc in (label, drawing):
            assert not doc.header['unreadable_pages'], 'An unreadable page was reported'
            assert all(i.evidence.page == 1 and i.evidence.bbox and i.evidence.extraction_method == 'ocr' for i in doc.items), 'Source evidence was not retained'
    print('PASS: scanned label REF, 2 quantities, drawing identity, 2 callouts and page evidence.')
    print('Default offline OCR: ' + available_engines()[0])


if __name__ == '__main__':
    main()

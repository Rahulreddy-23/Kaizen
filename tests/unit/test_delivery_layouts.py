"""Regressions for document layouts in the second BD test delivery; synthetic files only, no customer data."""

import pymupdf
import pytest

from kaizen.checks.bom_drawing import drawing_applicability, run_bom_drawing_check
from kaizen.checks.bom_label import run_bom_label_check
from kaizen.ingest import ocr
from kaizen.ingest.bom_pdf import parse_bom_pdf
from kaizen.ingest.detect import detect_doc_type
from kaizen.ingest.drawing_pdf import _clean_ocr_line, parse_drawing_pdf
from kaizen.ingest.label_pdf import parse_label_pdf
from kaizen.ingest.ocr import OcrResult
from kaizen.matching.components import component
from kaizen.matching.ladder import MatchLadder
from kaizen.matching.normalize import normalize
from kaizen.models import Classification, DocType, ItemCategory, Thresholds
from kaizen.terminology.store import RelationshipStore
from tests.unit.test_bom_label_check import bom_doc, label_doc
from tests.unit.test_pairing_engine import drawing_doc


def blank_pdf(path, width=792, height=612):
    with pymupdf.open() as pdf:
        pdf.new_page(width=width, height=height)
        pdf.save(path)
    return path


@pytest.mark.parametrize("name,kind", [
    ("BAW1234567.pdf", DocType.LABEL),  # released artwork number used for unit labels
    ("DWG1234567D.pdf", DocType.DRAWING),  # drawing numbers can end in a letter
    ("DWG1234567D.pdfNov022026085156.pdf", DocType.DRAWING),  # scanner appended a timestamp
    ("DWG1234567.pdfNov022026090018.pdf", DocType.DRAWING),
])
def test_released_document_numbers_route_image_only_files(name, kind, tmp_path):
    assert detect_doc_type(blank_pdf(tmp_path / name)) is kind


def test_letter_suffixed_drawing_number_ties_the_drawing_to_its_bom(tmp_path):
    path = tmp_path / "drawing.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=792, height=612)
        page.insert_text((60, 120), "END CAP", fontsize=9)
        page.insert_text((60, 132), "TAPON DEL EXTREMO", fontsize=9)
        # Title-block cells: the number sits under its caption, beside the revision cell.
        page.insert_text((600, 560), "DRAWING NO.", fontsize=6)
        page.insert_text((700, 560), "REV.", fontsize=6)
        page.insert_text((600, 575), "DWG1234567D", fontsize=9)
        page.insert_text((700, 575), "16", fontsize=9)
        pdf.save(path)
    drawing = parse_drawing_pdf(path)
    assert drawing.header["drawing_number"] == "DWG1234567D"
    bom = bom_doc([("X1", "CAP, END", "1"), ("DWG1234567D", "SINGLE TRAY ASSEMBLY", "0")])
    assert drawing_applicability(bom, drawing) is True


def test_ocr_reads_the_printed_page_not_form_covers_annotations_or_red_reviewer_ink():
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=400, height=200)
        page.insert_text((20, 50), "END CAP", fontsize=24)  # printed content
        page.draw_rect(pymupdf.Rect(250, 20, 380, 80), color=(0.86, 0.2, 0.15), fill=(0.86, 0.2, 0.15))  # red pen tick
        cover = pymupdf.Widget()  # document-control viewers hide this white cover with JavaScript
        cover.field_type, cover.field_name = pymupdf.PDF_WIDGET_TYPE_TEXT, "obscure"
        cover.rect, cover.fill_color = pymupdf.Rect(10, 10, 200, 70), (1, 1, 1)
        page.add_widget(cover)
        page.add_freetext_annot(pymupdf.Rect(20, 120, 380, 180), "Label checked by", fontsize=20, fill_color=(0, 0, 0))
        pixels = ocr.page_pixels(page, dpi=72)

    def dark(rect):
        return (pixels[rect[1]:rect[3], rect[0]:rect[2]].min(axis=2) < 100).mean()

    assert dark((20, 30, 120, 55)) > 0.05  # the printed words remain under the form cover
    assert dark((250, 20, 380, 80)) == 0 and pixels[50, 300].min() > 240  # red ink becomes paper
    assert dark((20, 120, 380, 180)) == 0  # the annotation is not drawn


def test_red_handwriting_leaves_no_readable_outline_but_black_print_survives():
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=400, height=120)
        page.insert_text((20, 60), "Saline 10 mL", fontsize=22)
        page.insert_text((200, 60), "Reviewer", fontsize=26, color=(0.86, 0.2, 0.15))  # signature beside the entry
        pixels = ocr.page_pixels(page, dpi=240)
    signature = pixels[100:220, 660:1300].astype(int)
    assert (signature.min(axis=2) > 225).all()  # no pink fringe that OCR could still read
    printed = pixels[100:220, 60:600]
    assert (printed.min(axis=2) < 100).mean() > 0.03


def picture(page, rect):
    """A raster picture on the page, as a pasted drawing or a scan would be."""
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 20), False)
    pix.clear_with(250)
    page.insert_image(rect, pixmap=pix, keep_proportion=False)


def stub_ocr(monkeypatch, words):
    """Page OCR returns `words` (text, x0, y0); the title-block revision crop finds nothing."""
    calls = []

    def fake(page, dpi=240, *, clip=None, single_line=False):
        if clip is not None:
            return ocr.OcrResult(engine="rapidocr-onnxruntime")
        calls.append(page.number + 1)
        boxes = [(x, y, x + 6.5 * len(text), y + 9, text, 0.9) for text, x, y in words.get(page.number + 1, [])]
        return ocr.OcrResult(words=boxes, engine="rapidocr-onnxruntime", dpi=dpi)

    monkeypatch.setattr("kaizen.ingest.drawing_pdf.ocr_available", lambda: True)
    monkeypatch.setattr("kaizen.ingest.drawing_pdf.ocr_page", fake)
    return calls


def test_document_control_export_reads_sheets_under_the_stamp_and_skips_the_signature_manifest(tmp_path, monkeypatch):
    path = tmp_path / "DWG1234567D.pdf"
    with pymupdf.open() as pdf:
        sheet = pdf.new_page(width=792, height=612)
        picture(sheet, pymupdf.Rect(40, 40, 400, 300))
        sheet.insert_text((420, 300), "Released", fontsize=40)  # document-control watermark
        manifest = pdf.new_page(width=612, height=792)
        for n, text in enumerate(["Signature Manifest", "Document Number: DWG1234567D", "Revision: 16", "Title: Single Tray Assembly",
                                  "Name/Signature", "Title", "Date", "Meaning/Reason", "Jane Doe (JDOE)", "Packaging Engineer", "Approved"]):
            manifest.insert_text((40, 60 + 18 * n), text, fontsize=10)
        more = pdf.new_page(width=612, height=792)
        for n, text in enumerate(["John Roe (JROE)", "DC Release", "Name/Signature", "Meaning/Reason", "Approved",
                                  "Published MasterControl documents frequently use JavaScript."]):
            more.insert_text((40, 60 + 18 * n), text, fontsize=10)
        pdf.save(path)
    calls = stub_ocr(monkeypatch, {1: [("END CAP", 60, 80), ("TAPON DEL EXTREMO", 60, 91), ("DWG1234567D", 600, 560)]})
    drawing = parse_drawing_pdf(path)
    assert calls == [1]
    assert [i.description for i in drawing.items] == ["END CAP"]
    assert (drawing.header["drawing_number"], drawing.header["revision"], drawing.header["title"]) == ("DWG1234567D", "16", "Single Tray Assembly")
    assert drawing.sku == "DWG1234567D" and drawing.header["unreadable_pages"] == []


TEMPLATE = ["MDS Example Site", "Document Type: Packaging Assembly Drawing", "Document No:", "DWG1234567", "Page No:", "1 of 2",
            "Title: MAX TRAY ASSEMBLY", "Revision No:", "00", "Owned by: SITE", "Used by: Plant",
            "THIS SUBJECT MATTER IS RESTRICTED SOLELY FOR THE USE OF THE COMPANY", "DWG_SITE [template] rev. 0"]


def template_page(pdf):
    page = pdf.new_page(width=792, height=612)
    for n, text in enumerate(TEMPLATE):
        page.insert_text((40 if n < 11 else 120, 20 + 9 * n if n < 11 else 560 + 12 * (n - 11)), text, fontsize=7)
    return page


def test_document_template_boilerplate_is_not_a_callout_and_names_the_drawing(tmp_path, monkeypatch):
    path = tmp_path / "DWG1234567.pdf"
    with pymupdf.open() as pdf:
        page = template_page(pdf)
        picture(page, pymupdf.Rect(40, 130, 740, 500))
        page.insert_text((40, 520), "Notes:", fontsize=8)
        page.insert_text((40, 530), "1. For component placement only.", fontsize=8)
        pdf.save(path)
    stub_ocr(monkeypatch, {1: [("SYRINGE LABEL", 80, 160), ("ETIQUETA DE LA JERINGA", 80, 171), ("THIS SUBJECT MATTER IS RESTRICTED SOLELY", 120, 562)]})
    drawing = parse_drawing_pdf(path)
    assert [i.description for i in drawing.items] == ["SYRINGE LABEL"]
    assert (drawing.header["drawing_number"], drawing.header["revision"], drawing.header["title"]) == ("DWG1234567", "00", "MAX TRAY ASSEMBLY")


def test_callouts_inside_a_pasted_picture_are_read_beside_native_text_boxes(tmp_path, monkeypatch):
    path = tmp_path / "DWG1234567.pdf"
    with pymupdf.open() as pdf:
        page = template_page(pdf)
        picture(page, pymupdf.Rect(40, 130, 560, 500))
        for n, text in enumerate(["PLACE THE NEEDLE IN A BAG FIRST", "COLOCAR LA AGUJA EN UNA BOLSA PRIMERO"]):
            page.insert_text((600, 200 + 10 * n), text, fontsize=6)  # a native text box beside the picture
        pdf.save(path)
    stub_ocr(monkeypatch, {1: [("BAGGED SYRINGE", 80, 160), ("JERINGA EMBOLSADA", 80, 171),
                               ("PLACE THE NEEDLE IN A BAG FIRST", 600, 193)]})  # OCR re-reads the text box too
    drawing = parse_drawing_pdf(path)
    descriptions = [i.description for i in drawing.items]
    assert sorted(descriptions) == ["BAGGED SYRINGE", "PLACE THE NEEDLE IN A BAG FIRST"]
    methods = {i.description: i.evidence.extraction_method for i in drawing.items}
    assert methods == {"PLACE THE NEEDLE IN A BAG FIRST": "pdf_text", "BAGGED SYRINGE": "ocr"}


def test_contents_line_missed_by_ocr_is_recovered_from_the_scanner_text_layer(tmp_path, monkeypatch):
    path = tmp_path / "LAB1234567.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        picture(page, page.rect)
        # The scanner's own text layer: complete contents, but REF printed as artwork.
        for text, y in [("Kit - Contents:", 50), ("1 Each - Mask", 60), ("1 Each • Gown, Surgical", 70), ("2 Each - Gloves", 80)]:
            page.insert_text((10, y), text, fontsize=8, render_mode=3)
        pdf.save(path)
    # Page OCR reads the REF but skips the whole Gown line.
    lines = [("REF 1234567D", 10, 10), ("Kit - Contents:", 10, 43), ("1 Each - Mask", 10, 53), ("2 Each - Gloves", 10, 73)]
    words = []
    for text, x, y in lines:
        for token in text.split():
            words.append((x, y, x + 4 * len(token), y + 8, token, .9))
            x += 4 * (len(token) + 1)
    result = OcrResult(words=words, engine="fake")
    monkeypatch.setattr("kaizen.ingest.label_pdf.ocr_available", lambda: True)
    monkeypatch.setattr("kaizen.ingest.label_pdf.ocr_page", lambda page: result)
    label = parse_label_pdf(path)
    assert [(i.description, str(i.quantity)) for i in label.items] == [("Mask", "1"), ("Gown, Surgical", "1"), ("Gloves", "2")]
    assert label.items[1].extraction_confidence < 1
    assert any("recovered 1 contents line" in w for w in label.warnings)


def test_abbreviated_introducer_needle_pairs_with_its_label_line():
    assert normalize("NEEDLE, INTRO, ECHOGENIC").normalized == "NEEDLE INTRODUCER ECHOGENIC"
    th = Thresholds()
    bom = bom_doc([("RM1234567", "NEEDLE, INTRO, ECHOGENIC", "1"), ("RM7654321", "SYRINGE, 10ML", "1")])
    label = label_doc([("Needle, Introducer, 21 G (70 mm Length)", "1"), ("Syringe, 10 mL", "1")])
    rows = {r.source_a.item_number: r for r in run_bom_label_check(bom, label, MatchLadder(RelationshipStore.default(), th), th) if r.role == "item" and r.source_a}
    assert rows["RM1234567"].source_b is not None and rows["RM1234567"].source_b.description.startswith("Needle, Introducer")
    assert rows["RM1234567"].classification is not Classification.MISSING and rows["RM1234567"].requires_validation


def test_left_column_text_running_past_the_right_column_start_stays_with_its_entry(tmp_path, monkeypatch):
    path = tmp_path / "LAB1234567.pdf"
    with pymupdf.open() as pdf:
        picture(pdf.new_page(), pymupdf.Rect(0, 0, 612, 792))
        pdf.save(path)
    lines = [("REF 1234567D", 10, 10), ("Kit - Contents:", 10, 43),
             ("1 Each - Mask", 10, 53), ("1 Each - End Cap", 300, 53),
             ("2 Each - Applicator (Tinted), 3", 10, 63), ("mL", 296, 63), ("1 Each - ECG Electrodes", 305, 63)]
    words = []
    for text, x, y in lines:
        for token in text.split():
            words.append((x, y, x + 4 * len(token), y + 8, token, .9))
            x += 4 * (len(token) + 1)
    monkeypatch.setattr("kaizen.ingest.label_pdf.ocr_available", lambda: True)
    monkeypatch.setattr("kaizen.ingest.label_pdf.ocr_page", lambda page: OcrResult(words=words, engine="fake"))
    label = parse_label_pdf(path)
    assert [i.description for i in label.items] == ["Mask", "Applicator (Tinted), 3 mL", "End Cap", "ECG Electrodes"]


@pytest.mark.parametrize("fused,split", [("SEALEDINNERPOUCH", "SEALED INNER POUCH"), ("IFU(UNDERCOMPONENTS) (REFERTOWORKORDER)", "IFU(UNDER COMPONENTS) (REFER TO WORK ORDER)"),
                                         ("DONOTCOVERPRINTING", "DO NOT COVER PRINTING"), ("UBICACIONAPROXIMADASOLAMENTE", "UBICACION APROXIMADA SOLAMENTE")])
def test_pouch_drawing_words_joined_by_ocr_are_separated(fused, split):
    assert _clean_ocr_line(fused) == split


def test_a_product_carton_is_packaging_not_the_product_it_holds():
    assert component(normalize("CARTON, PICC KIT").normalized).kind == "carton"
    th = Thresholds()
    bom = bom_doc([("SA1234567", "PICC, 5FR, TRIMMED", "1"), ("PK1234567", "CARTON, PICC KIT", "1", ItemCategory.PACKAGING)], parent="1234567J")
    rows = run_bom_drawing_check(bom, drawing_doc(["CATHETER", "CARTON"], number="DWG1234567"), MatchLadder(RelationshipStore.default(), th), th)
    pairs = {r.source_b.description: r.source_a.item_number for r in rows if r.role == "item" and r.source_a and r.source_b}
    assert pairs == {"CATHETER": "SA1234567", "CARTON": "PK1234567"}


def test_sub_assembly_lines_of_an_indented_bom_are_not_kit_contents():
    bom = bom_doc([("SA1234567", "MICROINTRO, 4FR X 5CM", "1"), ("RM1234567", "TUBING, SHEATH, 4FR", "1"),
                   ("SA7654321", "TACK, RETAINING", "2"), ("RM7654321", "IV CATHETER, SAFETY, 22G", "1")])
    for item, level in zip(bom.items, ("1", "2", "2", "1")):
        item.attributes["level"] = level
    th = Thresholds()
    ladder = MatchLadder(RelationshipStore.default(), th)
    label = label_doc([("Microintroducer, 4 F (5 cm Length)", "1"), ("IV Catheter, Safety, 22 G", "1")])
    rows = run_bom_label_check(bom, label, ladder, th)
    compared = {r.source_a.item_number for r in rows if r.role == "item" and r.source_a}
    assert compared == {"SA1234567", "RM7654321"}
    exempt = {r.source_a.item_number: r.explanation for r in rows if r.role == "exempt"}
    assert set(exempt) == {"RM1234567", "SA7654321"} and "level 2" in exempt["RM1234567"]
    drawing_rows = run_bom_drawing_check(bom, drawing_doc(["MICROINTRODUCER", "IV CATHETER"], number="DWG1234567"), ladder, th)
    assert {r.source_a.item_number for r in drawing_rows if r.role == "item" and r.source_a} == {"SA1234567", "RM7654321"}


@pytest.mark.parametrize("read,expected", [
    ("Elaslic Band", "Elastic Band"), ("IV Calheler, 22 G (25 mm Lenglh)", "IV Catheter, 22 G (25 mm Length)"),
    ("Drape, Feneslraled", "Drape, Fenestrated"), ("Gauze, 10 crn x 10 cm", "Gauze, 10 cm x 10 cm"),
    ("PICC, vith Stylet", "PICC, with Stylet"),
    ("Hollow Tube", "Hollow Tube"), ("Lidocaine HCl 1%", "Lidocaine HCl 1%"),  # unknown or correct words are never rewritten
])
def test_ocr_letter_confusions_are_corrected_only_to_known_label_words(read, expected):
    assert ocr.correct_confused_label_letters(read) == expected


def test_item_numbers_with_a_decimal_point_are_not_dropped(tmp_path):
    path = tmp_path / "bom.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=792, height=612)
        page.insert_text((20, 30), "Parent Item 1234567")
        for x, text in [(26, "Level"), (76, "Component Item"), (172, "Component Description"), (284, "Branch/Plant"), (349, "Quantity Per"), (451, "Ext Qty"), (558, "UM")]:
            page.insert_text((x, 70), text, fontsize=6)
        rows = [("1", "SA1234567", "MICROINTRO, 3.5FR X 7CM", "1.0000"), ("2", "RT-ABCDEF-3.5FR", "MICROINTRODUCER 3.5FR", "0.0000")]
        for n, (level, item, desc, qty) in enumerate(rows):
            for x, text in [(18, level), (60, item), (162, desc), (296, "5150"), (382, qty), (479, qty), (558, "EA")]:
                page.insert_text((x, 95 + 20 * n), text, fontsize=6)
        pdf.save(path)
    parsed = parse_bom_pdf(path)
    assert [i.item_number for i in parsed.items] == ["SA1234567", "RT-ABCDEF-3.5FR"]
    assert not parsed.header["unparsed_rows"]

import pymupdf

from kaizen.datasets.pdf_bom import AnnotationSpec, BomRowSpec, BomSpec, render_bom_pdf


def _spec(n_rows: int) -> BomSpec:
    rows = [BomRowSpec(item=f"{1000000 + i}", description=f"COMPONENT {i}", qty_per="1.0000") for i in range(n_rows)]
    return BomSpec(parent_item="1295108NS", parent_description="POWERPICC SOLO2 KIT", rows=rows)


def test_render_writes_header_and_rows(tmp_path):
    path = render_bom_pdf(_spec(3), tmp_path / "bom.pdf")
    doc = pymupdf.open(path)
    text = doc[0].get_text()
    assert "Bill of Material Print" in text
    assert "Parent Item" in text and "1295108NS" in text
    assert "Component Item" in text and "Component Description" in text and "Quantity Per" in text
    assert "1000002" in text and "COMPONENT 2" in text


def test_render_paginates(tmp_path):
    path = render_bom_pdf(_spec(30), tmp_path / "bom.pdf", rows_per_page=12)
    doc = pymupdf.open(path)
    assert len(doc) == 3
    assert "Component Item" in doc[2].get_text()  # header repeated on every page
    assert "1000029" in doc[2].get_text()


def test_render_places_freetext_annotation_on_requested_row(tmp_path):
    spec = _spec(3)
    spec.annotations = [AnnotationSpec(row_index=1, field="component_item", text="PK0722294")]
    path = render_bom_pdf(spec, tmp_path / "bom.pdf")
    doc = pymupdf.open(path)
    annots = list(doc[0].annots())
    assert len(annots) == 1
    assert annots[0].info["content"] == "PK0722294"

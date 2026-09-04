import pymupdf

from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf


def test_render_label_contains_ref_name_and_contents(tmp_path):
    spec = LabelSpec(
        ref="1295108",
        product_name="PowerPICC SOLO2 Catheter with Sherlock 3CG Tip Positioning System (TPS) Stylet",
        contents=["1 Each - Towel, Absorbent", "2 Each - Mask", "1 Each - Gloves (1 pair)", "10 Each - Gauze, 10 cm x 10 cm (4 in. x 4 in.)"],
    )
    path = render_label_pdf(spec, tmp_path / "label.pdf")
    text = pymupdf.open(path)[0].get_text()
    assert "1295108" in text
    assert "Full Kit - Contents:" in text
    assert "Towel, Absorbent" in text and "Gauze" in text
    assert text.count("1295108") >= 5  # peel-off sub-labels repeat the REF


def test_render_label_two_columns_and_wrapping(tmp_path):
    long = "1 Each - Dual-Lumen PICC, 5.0 F (1.81 mm OD) x 55 cm, with Sherlock 3CG TPS Stylet/T-Lock Assembly and Stylet Funnel"
    spec = LabelSpec(ref="1295108", product_name="Kit", contents=[long] + [f"1 Each - Item {i}" for i in range(9)])
    path = render_label_pdf(spec, tmp_path / "label.pdf")
    page = pymupdf.open(path)[0]
    words = page.get_text("words")
    x_starts = sorted({round(w[0]) for w in words if w[4] == "Each"})
    assert len(x_starts) >= 2  # two distinct column x positions
    assert "Funnel" in page.get_text()

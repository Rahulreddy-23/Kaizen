from kaizen.datasets._stable import stabilize_pdf

TRAILER_HEX = b"%PDF-1.7\nobj\ntrailer\n<</Size 16/Info 15 0 R/Root 1 0 R/ID[<9F2D9FE4FDC592711309D8575149E7DA><9F2D9FE4FDC592711309D8575149E7DA>]>>\nstartxref\n"
TRAILER_LITERAL = b"%PDF-1.7\nobj\ntrailer\n<</Size 16/Info 15 0 R/Root 1 0 R/ID[<7AC298055FC28EC290C2B5C3834DC29A>(9OU\\330\\376\\257TQP-\\3504J\\tU\\013)]>>\nstartxref\n"


def test_stabilize_handles_hex_and_literal_id_forms(tmp_path):
    outputs = []
    for raw in (TRAILER_HEX, TRAILER_LITERAL):
        path = tmp_path / "x.pdf"
        path.write_bytes(raw)
        stabilize_pdf(path)
        outputs.append(path.read_bytes())
    assert outputs[0] == outputs[1]
    assert b"/ID[<" in outputs[0] and b"(9OU" not in outputs[1]


def test_stabilize_leaves_files_without_id_untouched(tmp_path):
    path = tmp_path / "x.pdf"
    path.write_bytes(b"%PDF-1.7\ntrailer\n<</Size 3>>\n")
    stabilize_pdf(path)
    assert path.read_bytes() == b"%PDF-1.7\ntrailer\n<</Size 3>>\n"

"""Seeded scenarios for the golden dataset: ten SKUs in one product family, each mutating the base kit to plant
known cases. The ground truth is generated from these definitions, so it cannot drift from the documents."""

from dataclasses import dataclass, field, replace

from kaizen.datasets.catalog import DRAWING_REV, NON_PHYSICAL_HEAD, NON_PHYSICAL_TAIL, PHYSICAL
from kaizen.datasets.pco_docs import PcoRowSpec
from kaizen.datasets.pdf_bom import AnnotationSpec

PRODUCT_NAME = "PowerPICC SOLO2 Catheter with Sherlock 3CG Tip Positioning System (TPS) Stylet"
PARENT_DESC = "PICC SOLO2 KIT 5F DL SHERLOCK"


@dataclass(frozen=True)
class Expected:
    classification: str
    discrepancies: list[str]
    scenario: str
    label_any_of: list[str] | None = None


@dataclass(frozen=True)
class Line:
    item: str | None  # None → label-only line
    bom_desc: str | None
    bom_qty: str | None  # BOM 'Quantity Per' text; "" renders a blank cell (extraction-confidence case)
    label_text: str | None  # None → not printed on the label
    label_qty: int | None
    expected: Expected | None  # BOM ↔ Label; None → not compared (non-physical / inactive)
    t: str = "P"
    oper_seq: str = "7.00"
    eff_thru: str = "12/31/40"
    callout: str | None = None  # drawing callout (EN); None → not on the drawing
    callout_es: str | None = None
    expected_drawing: Expected | None = None  # BOM ↔ Drawing row for this BOM line
    expected_label_drawing: Expected | None = None  # Label ↔ Drawing row for this label line (or B-only when label_text is None)


@dataclass(frozen=True)
class ExtraCallout:
    en: str
    es: str
    conditional: bool = False
    expected_bom: Expected | None = None  # B-only BOM ↔ Drawing expectation (None → exempt / not scored)
    expected_label: Expected | None = None


@dataclass(frozen=True)
class PcoExpectation:
    change_key: str
    classification: str
    discrepancies: list[str]
    scenario: str


@dataclass(frozen=True)
class RevExpectation:
    change_key: str
    classification: str
    discrepancies: list[str]
    scenario: str


@dataclass
class Scenario:
    parent_item: str
    folder: str
    ref: str
    bom_format: str  # pdf | xlsx | csv
    lines: list[Line]
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    ref_check: str = "EXACT"
    product_name: str = PRODUCT_NAME
    parent_description: str = PARENT_DESC
    annotations: list[AnnotationSpec] = field(default_factory=list)
    pco_bom: list[PcoExpectation] = field(default_factory=list)
    drawing_rev: str = DRAWING_REV
    drawing_ref: str = "EXACT"
    extra_callouts: list[ExtraCallout] = field(default_factory=list)
    old_label: bool = False  # render label_old.pdf
    old_label_remove: list[str] = field(default_factory=list)  # label texts absent on the old revision
    old_label_add: list[str] = field(default_factory=list)  # full 'N Each - ...' lines present only on the old revision
    old_label_replace: dict[str, str] = field(default_factory=dict)  # new label text → old label text
    old_label_qty: dict[str, int] = field(default_factory=dict)  # label text → quantity on the old revision
    label_revision: list[RevExpectation] = field(default_factory=list)


SCISSORS_OLD = "1 Each - Scissors with Protector Tubing"
TRIMMING = "Catheter Trimming Device"
REV_HEADER_OK = RevExpectation("HEADER", "EXACT", [], "rev-header-unchanged")
REV_APPLIED = [
    REV_HEADER_OK,
    RevExpectation("REMOVED:Scissors with Protector Tubing", "EXACT", [], "rev-expected-removal"),
    RevExpectation(f"ADDED:{TRIMMING}", "EXACT", [], "rev-expected-addition"),
]


@dataclass
class PcoScenario:
    number: str
    revision: str
    branch: str
    affected_codes: list[str]
    rows: list[PcoRowSpec]
    fmt: str  # xlsx | pdf
    missing_codes: list[str] = field(default_factory=list)
    notes: str = ""


PCO_A_ROWS = [
    PcoRowSpec(item_actual="RM5002565", item_proposed="DELETE", description="SCISSORS WITH PROTECTOR TUBING"),
    PcoRowSpec(item_actual="", item_proposed="RM0737876", description="CATHETER TRIMMING DEVICE", qty_proposed="1", seq_proposed="7"),
    PcoRowSpec(item_actual="", item_proposed="PK0744425", description="IFU, CATH TRIMMING DEVICE", qty_proposed="1", seq_proposed="7"),
]
PCO_B_ROWS = [PcoRowSpec(item_actual="2370001", item_proposed="2370002", description="SHERLOCK SENSOR HOLDER V2", qty_actual="1", qty_proposed="1", seq_actual="7", seq_proposed="7")]
PCOS: list[PcoScenario] = [
    PcoScenario("PCO34590", "0", "5150", ["1175108NS", "1275108NS", "1295108FNS", "1295108NS", "1395108QNS", "9295108FNS", "1495108NS"], PCO_A_ROWS, "xlsx", missing_codes=["1495108NS"],
                notes="The brief's PCO: delete the scissors, add the catheter trimming device and its IFU. Affected code 1495108NS has no BOM in the set (coverage blocker)."),
    PcoScenario("PCO34591", "1", "5150", ["2131910NS", "2131910FNS"], PCO_B_ROWS, "pdf",
                notes="PDF form. Substitute the sensor holder with a V2 part: applied on 2131910NS, not applied on 2131910FNS."),
]
_PCO_A_OK = [
    PcoExpectation("DELETE:RM5002565", "EXACT", [], "pco-delete-applied"),
    PcoExpectation("ADD:RM0737876", "EXACT", [], "pco-add-applied"),
    PcoExpectation("ADD:PK0744425", "EXACT", [], "pco-add-applied"),
]


def _np(rows) -> list[Line]:
    return [Line(item, desc, qty, None, None, None, t=t, oper_seq=seq) for item, desc, qty, t, seq in rows]


def base_lines() -> list[Line]:
    physical = [
        Line(
            c.item, c.bom_desc, f"{c.qty}.0000", c.label_text, c.qty, Expected(c.expected, [], c.scenario), t=c.t, oper_seq=c.oper_seq,
            callout=c.callout, callout_es=c.callout_es,
            expected_drawing=Expected(c.expected_drawing, [], "drawing-" + c.expected_drawing.lower()) if c.callout else Expected("MISSING", ["MISSING_IN_DRAWING"], "missing-on-drawing"),
            expected_label_drawing=Expected(c.expected_label_drawing, [], "label-drawing-" + c.expected_label_drawing.lower()) if c.callout else Expected("MISSING", ["MISSING_IN_DRAWING"], "missing-on-drawing"),
        )
        for c in PHYSICAL
    ]
    return _np(NON_PHYSICAL_HEAD) + physical + _np(NON_PHYSICAL_TAIL)


MISSING_ON_DRAWING = Expected("MISSING", ["MISSING_IN_DRAWING"], "missing-on-drawing")
EXTRA_ON_DRAWING = Expected("MISSING", ["EXTRA_ON_DRAWING"], "extra-on-drawing")


def _edit(lines: list[Line], target: str, **changes) -> list[Line]:
    out = []
    hit = False
    for l in lines:
        if l.item == target:
            out.append(replace(l, **changes))
            hit = True
        else:
            out.append(l)
    if not hit:
        raise KeyError(target)
    return out


def _drop(lines: list[Line], item: str) -> list[Line]:
    return [l for l in lines if l.item != item]


def _insert_after(lines: list[Line], item: str, new: Line) -> list[Line]:
    out = []
    for l in lines:
        out.append(l)
        if l.item == item:
            out.append(new)
    return out


def s01() -> Scenario:
    return Scenario(
        "1295108NS", "sku-001", "1295108", "pdf", base_lines(), pco_bom=list(_PCO_A_OK),
        old_label=True, old_label_remove=[TRIMMING], old_label_add=[SCISSORS_OLD], label_revision=list(REV_APPLIED),
        tags=["non-physical", "wrapped-line", "parenthetical-quantity", "multipage", "exact", "reordered", "relationship", "potential-fuzzy", "abbreviation", "pco-applied", "rev-expected-changes"],
        notes="Clean baseline: every physical component is on the label with the right quantity. Exercises reordered wording, relationships, fuzzy potentials, wrapped label lines, the '(3 per)' idiom and 12 non-physical BOM rows that must not be flagged.",
    )


def s02() -> Scenario:
    lines = base_lines()
    lines = _edit(lines, "7770010", label_qty=8, expected=Expected("MISMATCH", ["QTY_MISMATCH"], "qty-mismatch"))
    lines = _edit(lines, "2260001", label_qty=1, expected=Expected("MISMATCH", ["QTY_MISMATCH"], "qty-mismatch"))
    rev = REV_APPLIED + [RevExpectation("QTY:Gauze, 10 cm x 10 cm (4 in. x 4 in.)", "MISMATCH", ["UNEXPECTED_LABEL_CHANGE"], "rev-unexpected-qty")]
    return Scenario("1295108FNS", "sku-002", "1295108", "pdf", lines, tags=["qty-mismatch", "rev-unexpected-change"], pco_bom=list(_PCO_A_OK), old_label=True, old_label_remove=[TRIMMING], old_label_add=[SCISSORS_OLD], old_label_qty={"Gauze, 10 cm x 10 cm (4 in. x 4 in.)": 10}, label_revision=rev, notes="Two quantity discrepancies: gauze 10 vs 8 (behind a relationship match) and end caps 2 vs 1 (exact description).")


def s03() -> Scenario:
    lines = base_lines()
    lines = _edit(lines, "2340001", label_text=None, label_qty=None, expected=Expected("MISSING", ["MISSING_IN_LABEL"], "missing-on-label"), expected_label_drawing=EXTRA_ON_DRAWING)
    lines = _insert_after(lines, "2350001", Line("2390001", "SPONGE APPLICATOR", "1.0000", None, None, None, eff_thru="12/31/20"))
    lines = _insert_after(lines, "RM0737876", Line("RM5002565", "SCISSORS WITH PROTECTOR TUBING", "1.0000", None, None, Expected("MISSING", ["MISSING_IN_LABEL"], "pco-delete-not-applied"), expected_drawing=MISSING_ON_DRAWING))
    pco = [PcoExpectation("DELETE:RM5002565", "MISMATCH", ["PCO_CHANGE_NOT_APPLIED"], "pco-delete-not-applied"), _PCO_A_OK[1], _PCO_A_OK[2]]
    return Scenario("1395108QNS", "sku-003", "1395108", "pdf", lines, tags=["missing-on-label", "inactive", "pco-not-applied"], pco_bom=pco, notes="Absorbent drape omitted from the label (must be reported). An expired BOM line (effective thru 12/31/20) is absent from the label and must NOT be reported. The scissors the PCO deletes are still on the BOM: PCO change not applied, and the label rightly does not list them.")


def s04() -> Scenario:
    lines = base_lines() + [Line(None, None, None, "Lubricating Jelly, 5 g", 1, Expected("MISSING", ["MISSING_IN_BOM"], "extra-label-item"), expected_label_drawing=MISSING_ON_DRAWING)]
    lines = _edit(lines, "RM0737876", bom_qty="2.0000", expected=Expected("MISMATCH", ["QTY_MISMATCH"], "pco-qty-mismatch"))
    pco = [_PCO_A_OK[0], PcoExpectation("ADD:RM0737876", "MISMATCH", ["PCO_QTY_SEQ_MISMATCH"], "pco-qty-mismatch"), _PCO_A_OK[2]]
    rev = REV_APPLIED + [RevExpectation("ADDED:Lubricating Jelly, 5 g", "MISMATCH", ["UNEXPECTED_LABEL_CHANGE"], "rev-unexpected-addition")]
    return Scenario("1175108NS", "sku-004", "1175108", "pdf", lines, tags=["extra-label-item", "pco-qty-mismatch", "rev-unexpected-change"], pco_bom=pco, old_label=True, old_label_remove=[TRIMMING, "Lubricating Jelly, 5 g"], old_label_add=[SCISSORS_OLD], label_revision=rev, notes="Label lists a lubricating jelly that is not on the BOM. The catheter trimming device was added with qty 2 instead of the PCO's 1: visible in both the PCO ↔ BOM and BOM ↔ Label checks.")


def s05() -> Scenario:
    return Scenario("1275108NS", "sku-005", "1275109", "pdf", base_lines(), tags=["ref-mismatch", "drawing-rev-mismatch"], ref_check="REF_PARENT_MISMATCH", pco_bom=list(_PCO_A_OK), drawing_rev="10", drawing_ref="DRAWING_REV_MISMATCH", notes="Label REF 1275109 does not belong to BOM parent 1275108NS: a blocker before any line comparison.")


def s06() -> Scenario:
    intro = "Needle, Introducer, 21 G (0.9 mm OD x 0.55 mm ID x 70 mm Length)"
    safety21 = "Needle, Safety Hypodermic, 21 G (0.8 mm OD x 40 mm Length)"
    lines = base_lines()
    lines = _edit(lines, "4460021", item="4460099", bom_desc="NEEDLE 21G", expected=Expected("POTENTIAL", ["AMBIGUOUS_MATCH"], "ambiguous", label_any_of=[intro, safety21]), expected_drawing=Expected("POTENTIAL", [], "drawing-potential"))
    lines.append(Line(None, None, None, safety21, 1, Expected("MISSING", ["MISSING_IN_BOM"], "ambiguous-extra"), expected_label_drawing=MISSING_ON_DRAWING))
    lines = _edit(lines, "RM0737876", label_text=None, label_qty=None, expected=Expected("MISSING", ["MISSING_IN_LABEL"], "label-not-updated"), expected_label_drawing=EXTRA_ON_DRAWING)
    rev = [REV_HEADER_OK, RevExpectation("SATISFIED:Scissors with Protector Tubing", "EXACT", [], "rev-already-absent"), RevExpectation(f"ABSENT:{TRIMMING}", "MISSING", ["EXPECTED_CHANGE_ABSENT"], "rev-expected-change-absent")]
    return Scenario("9295108FNS", "sku-006", "9295108", "pdf", lines, tags=["ambiguous", "label-not-updated", "rev-expected-change-absent"], pco_bom=list(_PCO_A_OK), old_label=True, label_revision=rev, notes="A terse BOM line 'NEEDLE 21G' fits two label lines equally well; the tool must say so instead of guessing. The label was never updated for the PCO: the catheter trimming device is on the BOM (and the drawing) but not on the label, and the old/new label comparison reports the expected addition as absent.")


def s07() -> Scenario:
    safety21 = "Needle, Safety Hypodermic, 21 G (0.8 mm OD x 40 mm Length)"
    saline = "Syringe, Sodium Chloride (Saline) 0.9%, 10 mL"
    lines = base_lines()
    lines = _insert_after(lines, "4470025", Line("4470021", "NEEDLE SAFETY HYPODERMIC 21G", "1.0000", safety21, 1, Expected("POTENTIAL", [], "similar-descriptions"), callout="SAFETY NEEDLE 21G", callout_es="AGUJA DE SEGURIDAD 21G", expected_drawing=Expected("POTENTIAL", [], "drawing-similar"), expected_label_drawing=Expected("POTENTIAL", [], "label-drawing-similar")))
    lines = _drop(lines, "4500010")
    lines = _insert_after(lines, "2380001", Line("4510010", "SYRINGE 10ML LUER LOCK", "1.0000", None, None, Expected("MISSING", ["MISSING_IN_LABEL"], "fuzzy-must-not-accept"), expected_drawing=MISSING_ON_DRAWING))
    # the family drawing still shows the saline syringe: the label line pairs with it, the BOM has no such line
    lines.append(Line(None, None, None, saline, 2, Expected("MISSING", ["MISSING_IN_BOM"], "fuzzy-must-not-accept"), callout="SALINE SYRINGE 0.9% 10 ML", callout_es="JERINGA SALINA 0.9% 10 ML", expected_drawing=EXTRA_ON_DRAWING, expected_label_drawing=Expected("POTENTIAL", [], "label-drawing-potential")))
    lines = _edit(lines, "2370001", item="2370002", bom_desc="SHERLOCK SENSOR HOLDER V2", label_text="Sherlock™ Sensor Holder V2", expected=Expected("EXACT", [], "pco-substitute-applied"), expected_drawing=Expected("POTENTIAL", [], "drawing-potential"), expected_label_drawing=Expected("POTENTIAL", [], "label-drawing-potential"))
    rev = [REV_HEADER_OK, RevExpectation("DESC:Sherlock™ Sensor Holder V2", "EXACT", [], "rev-expected-substitution")]
    return Scenario("2131910NS", "sku-007", "2131910", "pdf", lines, tags=["similar-descriptions", "fuzzy-must-not-accept", "pco-applied", "extra-on-drawing", "rev-expected-changes"], pco_bom=[PcoExpectation("SUBSTITUTE:2370001>2370002", "EXACT", [], "pco-substitute-applied")], old_label=True, old_label_replace={"Sherlock™ Sensor Holder V2": "Sherlock™ Sensor Holder"}, label_revision=rev, notes="Two safety needles differing only by gauge must pair correctly (numeric guard). A 10 mL luer-lock syringe on the BOM and a 10 mL saline syringe on the label share words but are different items: both must be reported as missing, not paired.")


def s08() -> Scenario:
    lines = base_lines()
    lines = _edit(lines, "2220001", bom_qty="6.0000", expected=Expected("POTENTIAL", ["QTY_MISMATCH"], "idiom-quantity"))
    lines = _edit(lines, "2300001", bom_qty="2.0000", expected=Expected("POTENTIAL", ["QTY_MISMATCH"], "idiom-quantity"))
    rev = [REV_HEADER_OK, RevExpectation("ABSENT:SHERLOCK SENSOR HOLDER V2", "MISSING", ["EXPECTED_CHANGE_ABSENT"], "rev-expected-change-absent")]
    return Scenario("2131910FNS", "sku-008", "2131910", "xlsx", lines, tags=["xlsx-bom", "idiom-quantity", "pco-not-applied", "rev-expected-change-absent"], pco_bom=[PcoExpectation("SUBSTITUTE:2370001>2370002", "MISMATCH", ["PCO_CHANGE_NOT_APPLIED"], "pco-substitute-not-applied")], old_label=True, label_revision=rev, notes="BOM delivered as an XLSX export. Tape strips 6 vs '2 Each (3 per)' and gloves 2 vs '1 Each (1 pair)': differences a label idiom can explain are flagged for the reviewer, not called mismatches.")


def s09() -> Scenario:
    lines = base_lines()
    lines = _edit(lines, "2330001", bom_qty="", expected=Expected("MISMATCH", ["QTY_MISMATCH", "LOW_EXTRACTION_CONFIDENCE"], "low-confidence"))
    lines = _edit(lines, "2240001", bom_desc="MASK PROCEDURE EARLOOP", expected=Expected("EQUIVALENT", [], "family-scoped-relationship"))
    case_label_index = next(i for i, l in enumerate(lines) if l.item == "BAW0722153")
    return Scenario(
        "3131910NS", "sku-009", "3131910", "pdf", lines, tags=["low-confidence", "family-scoped-relationship", "annotation-redline"],
        annotations=[AnnotationSpec(row_index=case_label_index, field="quantity_per", text="0.4000")],
        notes="A blank BOM quantity cell (low extraction confidence) must be surfaced, not silently treated as 1. The mask uses a family-scoped relationship. A FreeText redline annotation sits on the case-label row and is captured as evidence.",
    )


def s10() -> Scenario:
    lines = base_lines()
    lines = _edit(lines, "2240001", bom_desc="MASK PROCEDURE EARLOOP", expected=Expected("EQUIVALENT", [], "family-scoped-relationship"))
    return Scenario("3131910FNS", "sku-010", "3131910", "csv", lines, tags=["csv-bom", "family-scoped-relationship", "item-anchored-relationship"], notes="BOM delivered as CSV. Same family as sku-009, so the family-scoped mask relationship applies again.")


SCENARIOS: list[Scenario] = [s01(), s02(), s03(), s04(), s05(), s06(), s07(), s08(), s09(), s10()]

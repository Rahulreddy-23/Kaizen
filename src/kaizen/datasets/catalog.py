"""Component catalog for the synthetic product family, modelled on the PowerPICC kit in the brief.

Each physical component carries a terse ERP-style BOM description and the wording used on the label, plus the
classification the engine is EXPECTED to produce with the packaged default relationships. Expectations are
declared by hand here; the engine never reads them.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    item: str
    bom_desc: str
    label_text: str | None  # label wording after 'N Each - ' (idioms included); None → not printed on the label
    qty: int
    expected: str | None  # BOM ↔ Label: EXACT | EQUIVALENT | POTENTIAL | None (not compared)
    scenario: str
    callout: str | None = None  # drawing callout (English); None → not drawn
    callout_es: str | None = None
    expected_drawing: str | None = None  # BOM ↔ Drawing classification
    expected_label_drawing: str | None = None  # Label ↔ Drawing classification
    oper_seq: str = "7.00"
    t: str = "P"


PHYSICAL: list[Component] = [
    Component("3330010", "PICC DUAL LUMEN 5F 55CM SHERLOCK 3CG TPS", "Dual-Lumen PICC, 5.0 F (1.81 mm OD) x 55 cm, with Sherlock 3CG™ TPS Stylet/T-Lock Assembly and Stylet Funnel", 1, "EQUIVALENT", "wrapped-line", callout="PICC CATHETER 5F DUAL LUMEN", callout_es="CATETER PICC 5F DOBLE LUMEN", expected_drawing="EQUIVALENT", expected_label_drawing="EQUIVALENT"),
    Component("0396447", "ABSORBENT TOWEL", "Towel, Absorbent", 1, "EXACT", "reordered", callout="ABSORBENT TOWEL", callout_es="TOALLA ABSORBENTE", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("5167473", "TAPE ANCHOR PER-Q-CATH", "Surgical Tape", 1, "EQUIVALENT", "relationship", callout="SURGICAL TAPE", callout_es="CINTA QUIRURGICA", expected_drawing="EQUIVALENT", expected_label_drawing="EXACT"),
    Component("4410005", "SYRINGE 5ML", "Syringe, 5 mL", 1, "EXACT", "exact", callout="SYRINGE 5 ML", callout_es="JERINGA 5 ML", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("4420001", "STATLOCK STABILIZATION DEVICE", "StatLock™ Stabilization Device", 1, "EXACT", "exact", callout="STATLOCK STABILIZATION DEVICE", callout_es="DISPOSITIVO DE ESTABILIZACION STATLOCK", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("4430020", "INTRODUCER SAFETY IV CATH 20G", "Introducer, Safety Peripheral IV Catheter, 20 G (1.1 mm OD x 45 mm Length)", 1, "EQUIVALENT", "relationship", callout="SAFETY IV CATHETER INTRODUCER 20G", callout_es="INTRODUCTOR CATETER IV DE SEGURIDAD 20G", expected_drawing="EQUIVALENT", expected_label_drawing="EQUIVALENT"),
    Component("4440003", "CHLORAPREP APPLICATOR 3ML", "ChloraPrep™ Solution One-Step Applicator, 3 mL", 1, "POTENTIAL", "potential-fuzzy", callout="CHLORAPREP APPLICATOR 3 ML", callout_es="APLICADOR CHLORAPREP 3 ML", expected_drawing="EXACT", expected_label_drawing="POTENTIAL"),
    Component("4450001", "ASPIRATION DEVICE", "Aspiration Device", 1, "EXACT", "exact", callout="ASPIRATION DEVICE", callout_es="DISPOSITIVO DE ASPIRACION", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("2220001", "TAPE STRIPS", "Tape Strips (3 per)", 2, "EXACT", "parenthetical-quantity", callout="TAPE STRIPS", callout_es="TIRAS DE CINTA", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("7770010", "GAUZE 4X4", "Gauze, 10 cm x 10 cm (4 in. x 4 in.)", 10, "EQUIVALENT", "similar-descriptions", callout="GAUZE 4IN X 4IN", callout_es="GASA 4 X 4 PULG", expected_drawing="EQUIVALENT", expected_label_drawing="EQUIVALENT"),
    Component("7770005", "GAUZE 2X2", "Gauze, 5 cm x 5 cm (2 in. x 2 in.)", 6, "EQUIVALENT", "similar-descriptions", callout="GAUZE 2IN X 2IN", callout_es="GASA 2 X 2 PULG", expected_drawing="EQUIVALENT", expected_label_drawing="EQUIVALENT"),
    Component("2230001", "MEASURING TAPE", "Measuring Tape", 2, "EXACT", "exact", callout="TAPE MEASURE", callout_es="CINTA METRICA", expected_drawing="EQUIVALENT", expected_label_drawing="EQUIVALENT"),
    Component("2240001", "MASK PROCEDURE", "Mask", 2, "EQUIVALENT", "relationship", callout="MASK", callout_es="MASCARILLA", expected_drawing="EQUIVALENT", expected_label_drawing="EXACT"),
    Component("2250001", "DRESSING ADHESIVE", "Adhesive Dressing", 1, "EXACT", "reordered", callout="ADHESIVE DRESSING", callout_es="APOSITO ADHESIVO", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("2260001", "END CAP", "End Cap", 2, "EXACT", "exact", callout="END CAPS", callout_es="TAPAS DE EXTREMO", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("2270001", "WIPE ALCOHOL 70%", "Wipe, 70% Isopropyl Alcohol", 1, "POTENTIAL", "potential-fuzzy", callout="ALCOHOL WIPE 70%", callout_es="TOALLITA DE ALCOHOL 70%", expected_drawing="EXACT", expected_label_drawing="POTENTIAL"),
    Component("2280001", "ECG LEADS ASSY", "ECG Leads Assembly", 1, "EXACT", "abbreviation", callout="ECG LEADS ASSEMBLY", callout_es="CABLES ECG", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("2290001", "ELECTRODES ECG", "ECG Electrodes, 3 per pouch", 1, "EXACT", "reordered", callout="ECG ELECTRODES", callout_es="ELECTRODOS ECG", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("2300001", "GLOVES EXAM", "Gloves (1 pair)", 1, "EQUIVALENT", "item-anchored-relationship", callout="GLOVES", callout_es="GUANTES", expected_drawing="EQUIVALENT", expected_label_drawing="EXACT"),
    Component("2310001", "BAND ELASTIC BLUE", "Blue Elastic Band", 2, "EXACT", "reordered", callout="BLUE ELASTIC BAND", callout_es="BANDA ELASTICA AZUL", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("2320001", "HOLDER REMOTE CONTROL", "Remote Control Holder", 1, "EXACT", "reordered", callout="REMOTE CONTROL HOLDER", callout_es="SOPORTE DE CONTROL REMOTO", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("2330001", "TOURNIQUET", "Tourniquet", 1, "EXACT", "exact", callout="TOURNIQUET", callout_es="TORNIQUETE", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("RM0737876", "CATHETER TRIMMING DEVICE", "Catheter Trimming Device", 1, "EXACT", "exact", callout="CATHETER TRIMMING DEVICE", callout_es="DISPOSITIVO DE CORTE DEL CATETER", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("4460021", "NEEDLE INTRODUCER 21G", "Needle, Introducer, 21 G (0.9 mm OD x 0.55 mm ID x 70 mm Length)", 1, "POTENTIAL", "potential-fuzzy", callout="INTRODUCER NEEDLE 21G", callout_es="AGUJA INTRODUCTORA 21G", expected_drawing="EXACT", expected_label_drawing="POTENTIAL"),
    Component("2340001", "DRAPE ABSORBENT", "Drape, Absorbent", 1, "EXACT", "exact", callout="ABSORBENT DRAPE", callout_es="CAMPO ABSORBENTE", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("2350001", "DRAPE FENESTRATED", "Drape, Fenestrated", 1, "EXACT", "exact", callout="FENESTRATED DRAPE", callout_es="CAMPO FENESTRADO", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("4470025", "NEEDLE SAFETY HYPODERMIC 25G", "Needle, Safety Hypodermic, 25 G (0.5 mm OD x 16 mm Length)", 1, "POTENTIAL", "potential-fuzzy", callout="SAFETY NEEDLE 25G", callout_es="AGUJA DE SEGURIDAD 25G", expected_drawing="POTENTIAL", expected_label_drawing="POTENTIAL"),
    Component("2360001", "SCALPEL SAFETY", "Safety Scalpel", 1, "EXACT", "reordered", callout="SAFETY SCALPEL", callout_es="BISTURI DE SEGURIDAD", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("4480005", "MICROINTRODUCER MICROEZ 5F W/ DILATOR", "MicroEZ™ Microintroducer, 5.0 F (1.8 mm ID x 2.5 mm OD x 7 cm Length) with Vessel Dilator (0.5 mm ID)", 1, "POTENTIAL", "potential-fuzzy", callout="MICROINTRODUCER 5F WITH DILATOR", callout_es="MICROINTRODUCTOR 5F CON DILATADOR", expected_drawing="POTENTIAL", expected_label_drawing="POTENTIAL"),
    Component("2370001", "SHERLOCK SENSOR HOLDER", "Sherlock™ Sensor Holder", 1, "EXACT", "exact", callout="SHERLOCK SENSOR HOLDER", callout_es="SOPORTE DEL SENSOR SHERLOCK", expected_drawing="EXACT", expected_label_drawing="EXACT"),
    Component("4490046", "GUIDEWIRE FLEXURA NITINOL 0.018IN X 50CM", "Flexura™ Guidewire, Nitinol with Straight Tip, 0.46 mm (0.018 in.) OD x 50 cm, Bendable", 1, "POTENTIAL", "potential-fuzzy", callout="GUIDEWIRE 0.018 IN X 50 CM", callout_es="ALAMBRE GUIA 0.018 PULG X 50 CM", expected_drawing="POTENTIAL", expected_label_drawing="POTENTIAL"),
    Component("2380001", "LIDOCAINE HCL 1% 5ML AMPULE", "Lidocaine HCl 1%, 5 mL ampule", 1, "EXACT", "exact", callout="LIDOCAINE 1% 5 ML AMPULE", callout_es="AMPOLLA LIDOCAINA 1% 5 ML", expected_drawing="POTENTIAL", expected_label_drawing="POTENTIAL"),
    Component("4500010", "SYRINGE SALINE 0.9% 10ML", "Syringe, Sodium Chloride (Saline) 0.9%, 10 mL", 2, "POTENTIAL", "potential-fuzzy", callout="SALINE SYRINGE 0.9% 10 ML", callout_es="JERINGA SALINA 0.9% 10 ML", expected_drawing="EXACT", expected_label_drawing="POTENTIAL"),
]

# Lines that appear on every JDE BOM but never on a label. Quantities and flags follow the brief's example.
NON_PHYSICAL_HEAD: list[tuple[str, str, str, str, str]] = [
    # item, description, qty per, T flag, oper seq
    ("0703450", "LOD THERMAL TRANSFER RIBBON", "0.0000", "P", "5.00"),
    ("BAW0722153", "EN LOD, CASE LABEL", "0.4000", "Q", "5.00"),
    ("BAW0724416", "EN LOD, UNIT LABEL", "1.0000", "Q", "5.00"),
    ("C293054", "LABEL, PRIMING VOLUME, BLANK", "1.0000", "P", "5.00"),
    ("MPS0090", "PRODUCING LABELS ON THE", "0.0000", "Q", "5.00"),
    ("PK0722294", "CASE LABEL, BLANK", "0.4000", "P", "5.00"),
    ("PK0756181", "PORT ACCESS KIT LABEL STOCK", "1.0000", "P", "5.00"),
    ("FM00182", "FIRST/LAST LABEL RECORD", "0.0000", "Q", "6.00"),
    ("MPS0019", "PACKAGING QUALITY", "0.0000", "Q", "6.00"),
]
NON_PHYSICAL_TAIL: list[tuple[str, str, str, str, str]] = [
    ("PK0744425", "IFU, CATH TRIMMING DEVICE", "1.0000", "P", "7.00"),
    ("PK0100001", "TRAY, THERMOFORMED", "1.0000", "P", "8.00"),
    ("PK0100002", "CARTON, SHIPPER", "0.2500", "P", "9.00"),
    ("PK0100003", "TRAY ASSY PER DWG3173108 REV 11", "1.0000", "P", "8.00"),
]
# Callouts that appear on every tray drawing but are not kit components. (en, es, conditional)
DRAWING_EXTRAS: list[tuple[str, str, bool]] = [
    ("THERMOFORMED TRAY", "BANDEJA TERMOFORMADA", False),
    ("SYRINGE LABEL", "ETIQUETA DE LA JERINGA", False),
    ("SHARP HOLDER", "PORTA NAVAJA", True),
]
DRAWING_NUMBER, DRAWING_REV, DRAWING_TITLE, DRAWING_PLANT = "DWG3173108", "11", "FULL SINGLE TRAY ASSEMBLY", "REYNOSA, MEXICO"

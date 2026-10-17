"""Component identity candidates, never approved engineering equivalence.

ERP and customer descriptions often share a component type while spelling none
of its attributes alike. Typed values guard these suggestions; unknown values
remain unknown. No item numbers or customer SKU mappings live here.
"""

import re
from dataclasses import dataclass

NUMBER = r"(?:\d+(?:\.\d+)?|\.\d+)"
# Specific types precede general nouns. A stylet funnel is a part of a catheter
# assembly; it must never consume the complete catheter's label entry.
KINDS = (
    ("funnel", r"\bFUNNEL\b"),
    ("microintroducer", r"\b(?:MICROINTRO\w*|MICROEZ)\b"),
    # Object nouns win over the component they contain, protect or are used with.
    ("drape", r"\bDRAPE\b"),
    ("cover", r"\bCOVER\b"),
    ("needle_holder", r"\bNEEDLE\s+HOLDER\b"),
    ("glove_container", r"\bGLOVES?\s+(?:WALLET|BOX|POUCH)\b"),
    ("protective_tube", r"\b(?:PROTECTIVE|PROTECTION)\s+TUBE\b"),
    ("shipping_case", r"\b(?:SHIP(?:PING)?\s+CASE|CASE[ ,]+SHIP(?:PING)?)\b"),
    ("spacer", r"\b(?:INSERT[ ,]+SPACING|INSERT\s+SPACER|SPACER\s+INSERT)\b"),
    ("tray", r"\bTRAY\b"),
    ("picc", r"\b(?:PICC|PPICC|POWERPICC)\b"),
    ("iv_catheter", r"\bIV\b.*\bCATH|\bCATH(?:ETER)?\b.*\bIV\b"),
    ("securement", r"\bSTATLOCK\b|\bCATH(?:ETER)?\s+SECUREM|\bSTABILIZATION\s+DEVICE\b"),
    ("sensor_holder", r"\bSENSOR\s+HOLDER\b"),
    ("electrode", r"\bELECTRODES?\b|\bPRE.GELLED.*\bECG\b"),
    ("ecg_lead", r"\bECG\s+LEADS?\b"),
    ("guidewire", r"\b(?:GUIDEWIRE|GW)\b"),
    ("bouffant_cap", r"\bBOUFFANT\b"),
    ("end_cap", r"\bEND\s+CAP\b|\bCAP\s+DEAD\s+END\b"),
    ("measuring_tape", r"\b(?:MEASURING|MEASUARING)\s+(?:PAPER\s+)?TAPE\b|\bTAPE[,\s]+(?:MEASURE|MEASURING|MEASUARING)\b"),
    ("antiseptic", r"\b(?:CHLORAPREP|CPREP)\b"),
    ("alcohol_wipe", r"\bWIPES?\b.*\b(?:ALCOHOL|ISOPROPYL)\b"),
    ("lidocaine", r"\bLIDOCAINE\b"),
    ("stylet", r"\bSTYLET\b"),
    ("introducer_needle", r"\bSEC(?:URE)?LOC\s*\d|\bNEEDLE\b.*\bINTRODUCER\b|\bINTRODUCER\s+NEEDLE\b"),
    ("needle", r"\bNEEDLE\b"),
    ("syringe", r"\bSYRINGE\b"),
    ("gauze", r"\bGAUZE\b"),
    ("mask", r"\bMASK\b"),
    ("gown", r"\bGOWN\b"),
    ("glove", r"\bGLOVES?\b"),
    ("tourniquet", r"\bTOURNIQUET[EA]?\b"),
    ("elastic_band", r"\bBAND\b.*\b(?:POLYISOPRENE|ELASTIC|BLUE)\b|\bELASTIC\s+BANDS?\b"),
    ("dressing", r"\b(?:DRESSING|DRSG)\b"),
    ("scalpel", r"\bSCALPEL\b"),
    ("scissors", r"\bSCISSORS?\b"),
    ("trimming_device", r"\b(?:CATHETER\s+)?TRIMMING\s+DEVICE\b"),
    ("catheter", r"\bCATHETER\b"),
    ("towel", r"\bTOWEL\b"),
    ("case_sealing_tape", r"\bCASE\s+SEALING\s+TAPE\b"),
    ("tape", r"\bTAPE\b"),
)


@dataclass(frozen=True)
class Component:
    kind: str | None
    values: dict
    dimensions: tuple[tuple[float, float, str], ...]


def family(kind: str | None) -> str | None:
    return "needle" if kind in ("introducer_needle", "needle") else kind


def component(text: str) -> Component:
    s = text.upper().replace('×', 'X')
    s = re.sub(r"(?<=\d)(?=[A-Z])|(?<=[A-Z])(?=\d)", " ", s)
    # Spacing above must not destroy decimal values or the dimension X.
    # WITH introduces a secondary part, not the identity of the primary object.
    head = re.split(r"\bWITH\b", s, maxsplit=1)[0]
    kind = next((name for name, pattern in KINDS if re.search(pattern, head)), None)
    if re.search(r"\b(?:LABEL|STICKER|IFU)\b|\bHANG\s+TAG\b", head) or (re.search(r"\bINSERT\b", head) and kind != "spacer"):
        kind = "document_or_label"
    values = {}
    for key, pattern in (("volume_ml", rf"({NUMBER})\s*ML\b"),
                         ("gauge", rf"({NUMBER})\s*(?:G|GA|GAUGE)\b"),
                         ("french", rf"({NUMBER})\s*(?:FR|F)\b"),
                         ("concentration_pct", rf"({NUMBER})\s*%")):
        if match := re.search(pattern, head):
            values[key] = float(match[1])
    if kind not in ("needle", "introducer_needle", "iv_catheter"):
        values.pop("gauge", None)
    if kind in ("needle", "introducer_needle"):
        if diameter := re.search(rf"({NUMBER})\s*MM\b", head):
            values["nominal_diameter_mm"] = float(diameter[1])
    if match := re.search(r"\b(SINGLE|DUAL|TRIPLE)[- ]LUMEN\b|\b(SL|DL|TL)\b", head):
        values["lumens"] = {"SINGLE": 1, "DUAL": 2, "TRIPLE": 3, "SL": 1, "DL": 2, "TL": 3}[match[1] or match[2]]
    if kind == "antiseptic":
        if re.search(r"\b(?:CLEAR|UNTINTED)\b", head):
            values["tinted"] = False
        elif re.search(r"\b(?:ORANGE|TINTED)\b", head):
            values["tinted"] = True
    if kind == "drape":
        for modifier in ("ABSORBENT", "FENESTRATED"):
            if modifier in head:
                values["drape_kind"] = modifier
    if kind == "syringe" and re.search(r"\b(?:SALINE|SODIUM\s*CHLORIDE|NACL)\b", head):
        values["contents"] = "saline"
    dims = []
    pattern = rf'({NUMBER})\s*(MM|CM|IN(?:CH(?:ES)?)?|["″])?\s*X\s*({NUMBER})\s*(MM|CM|IN(?:CH(?:ES)?)?|["″])?'
    for m in re.finditer(pattern, head):
        unit = m[2] or m[4] or "unspecified"
        unit = "IN" if unit in ('"', '″') or unit.startswith('IN') else unit
        dims.append((float(m[1]), float(m[3]), unit))
    return Component(kind, values, tuple(dims))


def compatible(a: Component, b: Component, *, generic_catheter: bool = False) -> tuple[list[str], list[str]]:
    conflicts, shared = [], []
    generic_pair = generic_catheter and "catheter" in (a.kind, b.kind) and {a.kind, b.kind} <= {"catheter", "picc", "iv_catheter"}
    if a.kind and b.kind and a.kind != b.kind and not generic_pair:
        conflicts.append(f"component type {a.kind} versus {b.kind}")
    for key in a.values.keys() & b.values.keys():
        if a.values[key] != b.values[key]:
            conflicts.append(f"{key}: {a.values[key]} versus {b.values[key]}")
        else:
            shared.append(f"{key}={a.values[key]}")
    if a.kind == b.kind == "syringe" and a.values.get("contents") != b.values.get("contents"):
        conflicts.append("prefilled contents are not established on both sides")
    if a.kind == b.kind == "gauze" and a.dimensions and b.dimensions:
        def equal(x, y):
            ax, ay, au = x
            bx, by, bu = y
            if au == "unspecified" or bu == "unspecified":
                return sorted((ax, ay)) == sorted((bx, by))
            factor = {"MM": 1, "CM": 10, "IN": 25.4}
            left, right = sorted((ax * factor[au], ay * factor[au])), sorted((bx * factor[bu], by * factor[bu]))
            return all(abs(x - y) <= max(x, y) * .03 for x, y in zip(left, right))
        if not any(equal(x, y) for x in a.dimensions for y in b.dimensions):
            conflicts.append(f"gauze dimensions {a.dimensions} versus {b.dimensions}")
        else:
            shared.append("printed gauze dimensions agree; confirm any unspecified units")
    return conflicts, shared


def alternatives(text: str) -> tuple[str, ...]:
    """Explicit OR describes alternatives, never a learned equivalence.

    Keep phrases with a shared trailing object noun intact (e.g. PICC OR other
    catheter DRAPE); splitting those would turn a drape into a catheter.
    """
    if component(text).kind == "drape":
        return (text,)
    parts = tuple(re.split(r"\s+OR\s+", text, flags=re.IGNORECASE))
    return parts if len(parts) > 1 and all(component(p).kind for p in parts) else (text,)


PACKAGING_KINDS = frozenset({"glove_container", "protective_tube", "shipping_case", "spacer", "tray", "case_sealing_tape"})

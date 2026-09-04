"""Parser for packaging drawings (vector PDF): title block, and EN/ES paired callouts as items.

A drawing is a PRESENCE source, not a quantity source; callouts carry no quantity. Cavity labels, notes and the
title block are noise. EN/ES pairs are one callout: the English text is the description, Spanish is kept as
evidence in `attributes.es_text`. Conditional callouts '(IF APPLICABLE PER BOM)' are flagged, not dropped.
"""

import re
import statistics
import unicodedata
from pathlib import Path

import pymupdf

from kaizen.ingest.hashing import document_id, sha256_file
from kaizen.ingest.pdf_words import Word, extract_words, group_lines, line_bbox, line_text, split_line_by_gaps
from kaizen.models import DocType, Document, DocumentItem, Evidence, ItemCategory

PARSER_NAME = "drawing_pdf"
PARSER_VERSION = "1"

ES_MARKERS = set(
    """CON DE DEL LA EL LOS LAS PARA SEGUN SI O Y EN UN UNA TUBO AGUJA JERINGA JERINGAS TIJERAS ALAMBRE GUIA CINTA METRICA
    BANDEJA ETIQUETA TAPAS TAPA EXTREMO CAVIDAD CAVIDADES ESCALPELO PAJILLA FILTRO SEGURIDAD CATETER DENTRO PORTA NAVAJA
    INTRODUCTORA INTRODUCTOR MICROINTRODUCTOR PROTECTOR PROTECTORA CORTE DISPOSITIVO APLICA BILLETE MATERIALES COLOCAR
    CUALQUIERA PINZAS VISTA ALTERNA SENCILLO COLGANTE TOALLA ABSORBENTE MASCARILLA GUANTES GASA VENDA TORNIQUETE SOPORTE
    REMOTO APOSITO ADHESIVO TOALLITA ELECTRODOS CABLES BANDA ELASTICA AZUL RECORTE CAMPO FENESTRADO BISTURI DILATADOR
    LIDOCAINA AMPOLLA SOLUCION SALINA CLORURO SODIO APLICADOR ASPIRACION TIRAS QUIRURGICA MEDICION CUBIERTA CORRESPONDE
    INDICADAS SOLAMENTE ORDEN TRABAJO APLICABILIDAD CANTIDAD COMPONENTE CONTRARIO ESPECIFIQUE MENOS LUBRICANTE GEL
    SENSOR HIPODERMICA LUMEN DOBLE ESTILETE LAVADO ESTABILIZACION POSICIONAMIENTO""".split()
)
EN_MARKERS = set(
    """WITH OR IF PER THE AND FOR TUBE TUBING NEEDLE SYRINGE SYRINGES SCISSORS WIRE GUIDE TAPE MEASURE TRAY LABEL CAPS
    CAP END HOLDER STRAW FILTER SAFETY CATHETER INSIDE PROTECTIVE FORCEPS DEVICE TRIMMING SHARP APPLICABLE BOM PLACE
    EITHER CAVITY INTRODUCER MICROINTRODUCER SCALPEL TOWEL ABSORBENT MASK GLOVES GAUZE DRAPE TOURNIQUET DRESSING WIPE
    ALCOHOL ELECTRODES LEADS BAND ELASTIC BLUE REMOTE CONTROL STRIPS SURGICAL MEASURING LIDOCAINE AMPULE SOLUTION SALINE
    APPLICATOR ASPIRATION GUIDEWIRE DILATOR STABILIZATION HYPODERMIC JELLY LUBRICATING PICC STYLET FUNNEL ASSEMBLY
    FENESTRATED ADHESIVE ISOPROPYL SODIUM CHLORIDE NITINOL STRAIGHT TIP BENDABLE VESSEL POSITIONING SYSTEM NEEDLES""".split()
)
_NOISE_RE = re.compile(
    r"^(NOTES?|NOTAS?)\b|^CAVITY\b|^CAVIDAD\b|^TOLERANCES?\b|^INCHES\b|^ANGLES\b|^THIRD ANGLE|^UNLESS OTHERWISE|^INTERPRET DRAWING|^NOTICE:|^UNAUTHORIZED|"
    r"^DRAWING NO|^SCALE\b|^DO NOT SCALE|^SHEET\b|^TITLE\b|^SIZE\b|^PART NO|^REV\.|^DWN\b|^CHK\b|^Checked by|^BD$|^\d+\.\s|^\.?X{1,3}\s*±|^ALTERNATIVE VIEW|^ALTERNATE UNITS|^VISTA ALTERNA|"
    r"^[A-Z .]+,\s*(MEXICO|USA|MX)$|^DWG\d{5,}\b|^\d{1,3}$|^\s*(FOR COMPONENT|LA ORDEN|PARA LA COLOCACION)",
    re.IGNORECASE,
)
_COND_EN = re.compile(r"\(\s*IF APPLICABLE PER BOM\s*\)", re.IGNORECASE)
_PLACEMENT_RE = re.compile(r"\(\s*(PLACE IN [^)]*)\)", re.IGNORECASE)
_PAREN_RE = re.compile(r"\([^)]*\)")
_DRAWING_NO_RE = re.compile(r"DRAWING NO\.?\s*([A-Z0-9][A-Z0-9\-]{4,})", re.IGNORECASE)
_DWG_RE = re.compile(r"\b(DWG[0-9]{5,})\b")
_REV_RE = re.compile(r"(?<![A-Z])REV\.?\s*([A-Z0-9]{1,3})(?![A-Z0-9])")
_TITLE_RE = re.compile(r"\bTITLE\s*\n?\s*([^\n]+)")
_PLANT_RE = re.compile(r"^([A-Z][A-Z .]{2,},\s*(?:MEXICO|USA|PUERTO RICO|MX))$", re.MULTILINE)


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def is_spanish_line(line: str) -> bool:
    if any(unicodedata.category(c) == "Mn" for c in unicodedata.normalize("NFD", line)) or "Ñ" in line.upper():
        return True
    tokens = re.findall(r"[A-Z]+", _strip_accents(line).upper())
    es = sum(1 for t in tokens if t in ES_MARKERS)
    en = sum(1 for t in tokens if t in EN_MARKERS)
    return es > 0 and es > en


def _clusters(lines: list[list[Word]]) -> list[list[list[Word]]]:
    heights = [max(w.y1 for w in l) - min(w.y0 for w in l) for l in lines] or [7.0]
    h = statistics.median(heights)
    clusters: list[list[list[Word]]] = []
    for line in sorted(lines, key=lambda l: (min(w.y0 for w in l), min(w.x0 for w in l))):
        x0, y0 = min(w.x0 for w in line), min(w.y0 for w in line)
        home = None
        for c in clusters:
            last = c[-1]
            last_y0, last_y1 = min(w.y0 for w in last), max(w.y1 for w in last)
            # glyph boxes of consecutive lines overlap slightly (box height > line step), so a small negative
            # gap is normal; a gap wider than ~1.25 line heights starts a new callout
            if abs(min(w.x0 for w in last) - x0) <= 14 and y0 > last_y0 and y0 - last_y1 <= 1.25 * h:
                home = c
                break
        if home is None:
            clusters.append([line])
        else:
            home.append(line)
    return clusters


def _header(text: str) -> dict:
    header: dict = {}
    flat = " ".join(text.split())
    if m := _DRAWING_NO_RE.search(flat):
        header["drawing_number"] = m.group(1).upper()
    elif m := _DWG_RE.search(flat):
        header["drawing_number"] = m.group(1)
    if m := _REV_RE.search(flat):
        header["revision"] = m.group(1)
    if m := _TITLE_RE.search(text):
        header["title"] = m.group(1).strip()
    if m := _PLANT_RE.search(text):
        header["plant"] = m.group(1).strip()
    return header


def parse_drawing_pdf(path: Path | str) -> Document:
    path = Path(path)
    sha = sha256_file(path)
    doc_id = document_id("dwg", sha, path)
    pdf = pymupdf.open(path)
    header: dict = {}
    items: list[DocumentItem] = []
    warnings: list[str] = []
    n_callouts = 0
    for page in pdf:
        page_no = page.number + 1
        text = page.get_text()
        for k, v in _header(text).items():
            header.setdefault(k, v)
        words = extract_words(page)
        if not words:
            warnings.append(f"page {page_no}: no extractable text (image-only page?) — OCR is NOT IMPLEMENTED")
            continue
        raw_lines = group_lines(words, y_tol=2.5)
        heights = [max(w.y1 for w in l) - min(w.y0 for w in l) for l in raw_lines] or [7.0]
        gap = 2.5 * statistics.median(heights)
        lines = [frag for l in raw_lines for frag in split_line_by_gaps(l, gap)]
        for cluster in _clusters(lines):
            texts = [line_text(l) for l in cluster]
            if any(_NOISE_RE.search(t.strip()) for t in texts):
                continue
            en: list[str] = []
            es: list[str] = []
            for t in texts:
                # a callout is English lines followed by their Spanish translation; once Spanish starts, the
                # remaining lines (including marker-less continuations such as '"BOM")') belong to it
                if es or is_spanish_line(t) or (en and t.strip() == en[-1].strip()):
                    es.append(t)
                else:
                    en.append(t)
            en_text = " ".join(en).strip()
            if not en_text:
                continue
            conditional = bool(_COND_EN.search(en_text))
            en_text = _COND_EN.sub("", en_text)
            placement = None
            if m := _PLACEMENT_RE.search(en_text):
                placement = m.group(1).strip()
                en_text = _PLACEMENT_RE.sub("", en_text)
            en_text = " ".join(en_text.split()).strip(" ,;")
            if not en_text or not re.search(r"[A-Z]{2,}", en_text):
                continue
            es_text = " ".join(_PAREN_RE.sub("", " ".join(es)).split())
            n_callouts += 1
            bbox = line_bbox([w for l in cluster for w in l])
            items.append(
                DocumentItem(
                    id=f"{doc_id}:c{n_callouts}", doc_id=doc_id, doc_type=DocType.DRAWING, sku=header.get("drawing_number"), description=en_text, quantity=None,
                    category=ItemCategory.PHYSICAL_COMPONENT, category_reason="drawing callout (presence only; the drawing is not a quantity source)",
                    attributes={"kind": "callout", "es_text": es_text, "conditional": conditional, "placement": placement, "callout_index": n_callouts, "sheet": page_no},
                    evidence=Evidence(file=str(path), file_sha256=sha, page=page_no, bbox=bbox, raw_text=" / ".join(texts), locator=f"sheet {page_no}, callout {n_callouts}"),
                )
            )
    pdf.close()
    if not items and not any("no extractable" in w for w in warnings):
        warnings.append("no callouts found on the drawing")
    if "drawing_number" not in header:
        warnings.append("drawing number not found in title block")
    return Document(id=doc_id, doc_type=DocType.DRAWING, path=str(path), sha256=sha, sku=header.get("drawing_number"), header=header, items=items, parser_name=PARSER_NAME, parser_version=PARSER_VERSION, warnings=warnings)

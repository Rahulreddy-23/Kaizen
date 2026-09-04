"""Enumerations shared across the engine. Names are stable identifiers used in reports and ground truth."""

from enum import Enum


class DocType(str, Enum):
    BOM = "BOM"
    LABEL = "LABEL"
    DRAWING = "DRAWING"
    PCO = "PCO"


class ItemCategory(str, Enum):
    """What a document line *is*. Only PHYSICAL_COMPONENT lines are expected on a product label."""

    PHYSICAL_COMPONENT = "PHYSICAL_COMPONENT"
    PACKAGING = "PACKAGING"
    LABEL = "LABEL"
    DOCUMENT = "DOCUMENT"  # IFU, inserts, printed documentation shipped with the product
    PROCESS = "PROCESS"
    QUALITY = "QUALITY"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    UNKNOWN = "UNKNOWN"


class Classification(str, Enum):
    EXACT = "EXACT"
    EQUIVALENT = "EQUIVALENT"
    POTENTIAL = "POTENTIAL"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"


class MatchLevel(str, Enum):
    """Which rung of the match ladder produced the pairing."""

    EXACT = "L1_EXACT"
    RELATIONSHIP = "L2_RELATIONSHIP"
    FUZZY = "L3_FUZZY"
    SEMANTIC = "L4_SEMANTIC"  # PLANNED — not implemented in week 1
    LLM = "L5_LLM"  # PLANNED — not implemented in week 1
    NONE = "NONE"


class DiscrepancyType(str, Enum):
    QTY_MISMATCH = "QTY_MISMATCH"
    DESC_MISMATCH = "DESC_MISMATCH"
    MISSING_IN_LABEL = "MISSING_IN_LABEL"
    MISSING_IN_BOM = "MISSING_IN_BOM"
    REF_PARENT_MISMATCH = "REF_PARENT_MISMATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    LOW_EXTRACTION_CONFIDENCE = "LOW_EXTRACTION_CONFIDENCE"
    # Reserved for later checks (drawing, PCO, label revisions)
    MISSING_IN_DRAWING = "MISSING_IN_DRAWING"
    EXTRA_ON_DRAWING = "EXTRA_ON_DRAWING"
    PCO_CHANGE_NOT_APPLIED = "PCO_CHANGE_NOT_APPLIED"
    PCO_QTY_SEQ_MISMATCH = "PCO_QTY_SEQ_MISMATCH"
    BOM_MISSING_FOR_AFFECTED_CODE = "BOM_MISSING_FOR_AFFECTED_CODE"
    UNEXPECTED_LABEL_CHANGE = "UNEXPECTED_LABEL_CHANGE"
    EXPECTED_CHANGE_ABSENT = "EXPECTED_CHANGE_ABSENT"
    DRAWING_REV_MISMATCH = "DRAWING_REV_MISMATCH"


class Severity(str, Enum):
    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


class CheckType(str, Enum):
    BOM_LABEL = "BOM_LABEL"
    BOM_DRAWING = "BOM_DRAWING"  # PLANNED
    LABEL_DRAWING = "LABEL_DRAWING"  # PLANNED
    PCO_BOM = "PCO_BOM"  # PLANNED
    LABEL_REVISION = "LABEL_REVISION"  # PLANNED

"""Ground-truth schema for the golden dataset. Hand-declared expectations; never derived from the engine."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from kaizen.models import Classification, DiscrepancyType


class ExpectedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bom_item: str | None = None
    label: str | None = None
    label_any_of: list[str] | None = None
    drawing: str | None = None
    drawing_any_of: list[str] | None = None
    classification: Classification
    discrepancies: list[DiscrepancyType] = Field(default_factory=list)
    scenario: str = ""
    note: str = ""

    def acceptable_labels(self) -> list[str | None]:
        return list(self.label_any_of) if self.label_any_of else [self.label]

    def acceptable_drawings(self) -> list[str | None]:
        return list(self.drawing_any_of) if self.drawing_any_of else [self.drawing]


class ExpectedPcoRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    change_key: str
    classification: Classification
    discrepancies: list[DiscrepancyType] = Field(default_factory=list)
    scenario: str = ""
    note: str = ""


class ExpectedRevisionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    change_key: str  # HEADER | REMOVED:<text> | ADDED:<text> | QTY:<text> | DESC:<text> | ABSENT:<text> | SATISFIED:<text>
    classification: Classification
    discrepancies: list[DiscrepancyType] = Field(default_factory=list)
    scenario: str = ""


class ExpectedSku(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folder: str = ""
    ref_check: str = "EXACT"  # "EXACT" or a DiscrepancyType name such as REF_PARENT_MISMATCH
    expected: list[ExpectedRow] = Field(default_factory=list)  # BOM ↔ Label rows
    bom_drawing: list[ExpectedRow] = Field(default_factory=list)  # BOM ↔ Drawing rows (bom_item ↔ drawing)
    label_drawing: list[ExpectedRow] = Field(default_factory=list)  # Label ↔ Drawing rows (label ↔ drawing)
    drawing_ref: str = "EXACT"  # EXACT | POTENTIAL (no BOM reference) | DRAWING_REV_MISMATCH
    label_revision: list[ExpectedRevisionRow] = Field(default_factory=list)
    pco_bom: list[ExpectedPcoRow] = Field(default_factory=list)  # PCO ↔ BOM rows (keyed by change)
    not_compared: list[str] = Field(default_factory=list)
    note: str = ""


class MissingBom(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pco: str
    code: str


class CoverageExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    missing_boms: list[MissingBom] = Field(default_factory=list)


class GroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = 1
    description: str = ""
    skus: dict[str, ExpectedSku]
    coverage: CoverageExpectation = Field(default_factory=CoverageExpectation)


def load_ground_truth(path: Path | str) -> GroundTruth:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return GroundTruth.model_validate(data)

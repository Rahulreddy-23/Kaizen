"""Canonical representation of a parsed document and its comparable lines."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from .enums import DocType, ItemCategory
from .evidence import Evidence


class SubQuantity(BaseModel):
    """Parenthetical quantity idiom on a label line, e.g. '(3 per)', '(1 pair)'."""

    value: int = Field(ge=1)
    kind: str = Field(description="per | pair | pack | each | other")
    raw: str


class DocumentItem(BaseModel):
    id: str
    doc_id: str
    doc_type: DocType
    sku: str | None = None
    item_number: str | None = None
    description: str
    quantity: Decimal | None = None
    uom: str | None = None
    oper_seq: str | None = None
    sub_quantity: SubQuantity | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    category: ItemCategory
    category_reason: str = ""
    is_active: bool = True
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: Evidence


class Document(BaseModel):
    id: str
    doc_type: DocType
    path: str
    sha256: str = Field(min_length=64, max_length=64)
    sku: str | None = Field(default=None, description="BOM parent item, label REF, etc.")
    header: dict[str, Any] = Field(default_factory=dict)
    items: list[DocumentItem] = Field(default_factory=list)
    parser_name: str
    parser_version: str
    warnings: list[str] = Field(default_factory=list)

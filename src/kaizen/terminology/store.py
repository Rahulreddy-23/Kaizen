"""Relationship store: explicit, versioned, scope-aware terminology knowledge."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kaizen.ingest.grouping import family_of
from kaizen.matching.normalize import NormalizedText, normalize
from kaizen.models import DocType, Relationship

_DEFAULT_PATH = Path(__file__).with_name("default_relationships.json")
_ID_RE = re.compile(r"^REL-(\d+)$")


@dataclass(frozen=True)
class RelationshipHit:
    relationship: Relationship
    kind: str  # "term" (both terms belong to the relationship) | "anchor" (item number anchored)
    specificity: int  # 0 global, 1 family, 2 sku


@dataclass(frozen=True)
class Snapshot:
    version: str
    count: int
    active_count: int
    relationships: list[dict[str, Any]]


class RelationshipStore:
    def __init__(self, relationships: list[Relationship] | tuple[Relationship, ...] = ()):
        self._items: dict[str, Relationship] = {}
        for r in relationships:
            self._items[r.id] = r
        self._keys: dict[str, set[str]] = {}
        self._reindex()

    # ---- persistence -------------------------------------------------------------------------
    @classmethod
    def load(cls, path: Path | str) -> "RelationshipStore":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls([Relationship.model_validate(r) for r in data.get("relationships", [])])

    @classmethod
    def default(cls) -> "RelationshipStore":
        return cls.load(_DEFAULT_PATH)

    def save(self, path: Path | str) -> None:
        payload = {"version": 1, "relationships": [r.model_dump(mode="json") for r in self.all(active_only=False)]}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    # ---- CRUD --------------------------------------------------------------------------------
    def next_id(self) -> str:
        nums = [int(m.group(1)) for rid in self._items if (m := _ID_RE.match(rid))]
        return f"REL-{(max(nums) + 1 if nums else 1):03d}"

    def add(self, canonical: str, aliases: list[str] | tuple[str, ...] = (), **fields: Any) -> Relationship:
        rel = Relationship(id=fields.pop("id", None) or self.next_id(), canonical=canonical, aliases=list(aliases), **fields)
        self._items[rel.id] = rel
        self._reindex()
        return rel

    def update(self, rel_id: str, **fields: Any) -> Relationship:
        rel = self._items[rel_id].model_copy(update=fields)
        rel = Relationship.model_validate(rel.model_dump())
        self._items[rel_id] = rel
        self._reindex()
        return rel

    def remove(self, rel_id: str) -> None:
        self._items.pop(rel_id, None)
        self._reindex()

    def get(self, rel_id: str) -> Relationship | None:
        return self._items.get(rel_id)

    def all(self, active_only: bool = True) -> list[Relationship]:
        rels = sorted(self._items.values(), key=lambda r: r.id)
        return [r for r in rels if r.active] if active_only else rels

    # ---- lookup ------------------------------------------------------------------------------
    def _reindex(self) -> None:
        self._keys = {rid: {normalize(t).sorted_key for t in r.terms()} for rid, r in self._items.items()}

    @staticmethod
    def _specificity(rel: Relationship, sku: str | None) -> int | None:
        if rel.scope == "global":
            return 0
        kind, _, value = rel.scope.partition(":")
        if sku is None:
            return None
        if kind == "family" and family_of(sku) == value:
            return 1
        if kind == "sku" and sku == value:
            return 2
        return None

    def lookup(
        self,
        a: NormalizedText | str,
        b: NormalizedText | str,
        *,
        sku: str | None = None,
        item_number: str | None = None,
        doc_types: tuple[DocType, ...] = (),
    ) -> RelationshipHit | None:
        """Find the most specific active relationship relating a and b.

        `item_number` is side A's item number (e.g. the BOM component). An item-anchored relationship matches
        when that number is anchored AND side B's wording is one of the relationship's terms — side A's own
        wording is deliberately irrelevant, that is what anchoring is for.
        """
        a_key = (a if isinstance(a, NormalizedText) else normalize(a)).sorted_key
        b_key = (b if isinstance(b, NormalizedText) else normalize(b)).sorted_key
        best: RelationshipHit | None = None
        for rel in self.all(active_only=True):
            spec = self._specificity(rel, sku)
            if spec is None:
                continue
            if rel.doc_types and doc_types and not set(doc_types) <= set(rel.doc_types):
                continue
            keys = self._keys[rel.id]
            kind: str | None = None
            if a_key in keys and b_key in keys:
                kind = "term"
            elif item_number and item_number in rel.item_anchors and b_key in keys:
                kind = "anchor"  # side A is identified by its item number; side B's wording must be a known term
            if kind and (best is None or spec > best.specificity):
                best = RelationshipHit(rel, kind, spec)
        return best

    def snapshot(self) -> Snapshot:
        rels = [r.model_dump(mode="json") for r in self.all(active_only=False)]
        digest = hashlib.sha256(json.dumps(rels, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return Snapshot(version=digest, count=len(rels), active_count=sum(1 for r in rels if r["active"]), relationships=rels)

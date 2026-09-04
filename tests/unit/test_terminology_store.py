import json

import pytest

from kaizen.matching.normalize import normalize
from kaizen.models import DocType, Relationship
from kaizen.terminology.store import RelationshipStore


@pytest.fixture
def store():
    return RelationshipStore(
        [
            Relationship(id="REL-001", canonical="Surgical Tape", aliases=["Tape Anchor Per-Q-Cath", "Tape Anchor"]),
            Relationship(id="REL-002", canonical="Measuring Tape", aliases=["Tape Measure"]),
            Relationship(id="REL-003", canonical="Towel, Absorbent", aliases=["ABSORBENT TOWEL"], scope="family:1295108"),
            Relationship(id="REL-004", canonical="Mask", aliases=["FACE MASK PROCEDURE"], scope="sku:1295108NS"),
            Relationship(id="REL-005", canonical="Gloves", item_anchors=["4440001"]),
            Relationship(id="REL-006", canonical="Old Thing", aliases=["OLD"], active=False),
        ]
    )


def test_global_term_lookup_returns_hit_with_id(store):
    hit = store.lookup(normalize("TAPE ANCHOR PER-Q-CATH"), normalize("Surgical Tape"))
    assert hit is not None
    assert hit.relationship.id == "REL-001"
    assert hit.kind == "term"


def test_lookup_is_symmetric(store):
    assert store.lookup(normalize("Surgical Tape"), normalize("TAPE ANCHOR")).relationship.id == "REL-001"


def test_no_hit_across_relationships(store):
    assert store.lookup(normalize("Surgical Tape"), normalize("Tape Measure")) is None


def test_inactive_relationships_are_ignored(store):
    assert store.lookup(normalize("OLD"), normalize("Old Thing")) is None


def test_family_scope(store):
    a, b = normalize("ABSORBENT TOWEL"), normalize("Towel, Absorbent")
    assert store.lookup(a, b, sku="1295108NS").relationship.id == "REL-003"
    assert store.lookup(a, b, sku="1295108FNS").relationship.id == "REL-003"
    assert store.lookup(a, b, sku="7770001NS") is None
    assert store.lookup(a, b) is None


def test_sku_scope(store):
    a, b = normalize("FACE MASK PROCEDURE"), normalize("Mask")
    assert store.lookup(a, b, sku="1295108NS").relationship.id == "REL-004"
    assert store.lookup(a, b, sku="1295108FNS") is None


def test_item_anchor_lookup(store):
    hit = store.lookup(normalize("GLOVE EXAM NITRILE"), normalize("Gloves"), item_number="4440001")
    assert hit.relationship.id == "REL-005"
    assert hit.kind == "anchor"
    assert store.lookup(normalize("GLOVE EXAM NITRILE"), normalize("Gloves"), item_number="0000000") is None


def test_doc_type_restriction():
    s = RelationshipStore([Relationship(id="REL-010", canonical="A", aliases=["B"], doc_types=[DocType.BOM, DocType.DRAWING])])
    assert s.lookup(normalize("A"), normalize("B"), doc_types=(DocType.BOM, DocType.LABEL)) is None
    assert s.lookup(normalize("A"), normalize("B"), doc_types=(DocType.BOM, DocType.DRAWING)) is not None
    assert s.lookup(normalize("A"), normalize("B")) is not None


def test_most_specific_scope_wins():
    s = RelationshipStore(
        [
            Relationship(id="REL-G", canonical="A", aliases=["B"]),
            Relationship(id="REL-S", canonical="A", aliases=["B"], scope="sku:1295108NS"),
        ]
    )
    assert s.lookup(normalize("A"), normalize("B"), sku="1295108NS").relationship.id == "REL-S"
    assert s.lookup(normalize("A"), normalize("B"), sku="OTHER").relationship.id == "REL-G"


def test_crud_and_persistence(tmp_path, store):
    rel = store.add(canonical="Drape, Fenestrated", aliases=["DRAPE FENESTRATED"], created_by="tester")
    assert rel.id == "REL-007"
    assert rel.provenance == "manual"
    store.update("REL-007", aliases=["DRAPE FENESTRATED", "FENESTRATED DRAPE"], notes="added alias")
    assert "FENESTRATED DRAPE" in store.get("REL-007").aliases
    store.remove("REL-002")
    assert store.get("REL-002") is None
    path = tmp_path / "rels.json"
    store.save(path)
    reloaded = RelationshipStore.load(path)
    assert reloaded.get("REL-007").notes == "added alias"
    assert reloaded.get("REL-002") is None
    assert json.loads(path.read_text())["version"] == 1


def test_snapshot_hash_changes_with_content(store):
    before = store.snapshot()
    store.add(canonical="X", aliases=["Y"])
    after = store.snapshot()
    assert before.version != after.version
    assert len(before.version) == 64
    assert after.count == before.count + 1
    assert before.version == store.__class__(store.all(active_only=False)[: before.count]).snapshot().version


def test_default_store_loads_packaged_relationships():
    s = RelationshipStore.default()
    assert s.lookup(normalize("TAPE ANCHOR PER-Q-CATH"), normalize("Surgical Tape")) is not None


def test_item_anchor_does_not_match_arbitrary_other_side(store):
    # Regression: an anchored BOM item must only resolve to the relationship's own terms on the other side.
    hit = store.lookup(normalize("GLOVES EXAM"), normalize("Dual-Lumen PICC, 5.0 F x 55 cm"), item_number="4440001")
    assert hit is None

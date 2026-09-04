import pytest

from kaizen.models import DocType, Relationship
from kaizen.terminology.repository import TerminologyRepository


@pytest.fixture
def repo(tmp_path):
    r = TerminologyRepository(tmp_path / "kaizen.db")
    r.initialize()  # seeds packaged defaults into an empty database
    return r


def test_initialize_seeds_defaults_once(repo, tmp_path):
    rels = repo.list()
    assert any(r.id == "REL-001" for r in rels)
    assert all(r.version == 1 for r in rels)
    again = TerminologyRepository(tmp_path / "kaizen.db")
    again.initialize()
    assert len(again.list()) == len(rels)


def test_create_assigns_next_id_and_version_one(repo):
    rel = repo.create(canonical="Drape, Fenestrated", aliases=["DRAPE FENESTRATED"], created_by="tester", notes="from test")
    assert rel.id.startswith("REL-") and rel.version == 1
    assert repo.get(rel.id).canonical == "Drape, Fenestrated"
    assert repo.get(rel.id).created_by == "tester"
    assert repo.history(rel.id)[0].change_type == "create"


def test_update_bumps_version_and_keeps_history(repo):
    rel = repo.create(canonical="Mask", aliases=["MASK PROCEDURE"], created_by="tester")
    updated = repo.update(rel.id, changed_by="editor", change_note="add alias", aliases=["MASK PROCEDURE", "FACE MASK"])
    assert updated.version == 2
    assert updated.updated_at >= rel.updated_at
    hist = repo.history(rel.id)
    assert [h.version for h in hist] == [1, 2]
    assert hist[1].change_type == "update" and hist[1].change_note == "add alias" and hist[1].changed_by == "editor"
    assert repo.get_version(rel.id, 1).aliases == ["MASK PROCEDURE"]
    assert repo.get_version(rel.id, 2).aliases == ["MASK PROCEDURE", "FACE MASK"]


def test_deactivate_activate_and_delete_are_versioned(repo):
    rel = repo.create(canonical="Old", aliases=["OLD THING"], created_by="t")
    repo.deactivate(rel.id, changed_by="t", change_note="obsolete")
    assert repo.get(rel.id).active is False
    assert rel.id not in {r.id for r in repo.store().all()}
    repo.activate(rel.id, changed_by="t")
    assert repo.get(rel.id).active is True
    repo.delete(rel.id, changed_by="t", change_note="wrong entry")
    assert repo.get(rel.id) is None
    hist = repo.history(rel.id)
    assert [h.change_type for h in hist] == ["create", "deactivate", "activate", "delete"]
    assert repo.get_version(rel.id, 1).canonical == "Old"  # history survives deletion


def test_store_reflects_active_relationships_for_matching(repo):
    from kaizen.matching.normalize import normalize

    store = repo.store()
    assert store.lookup(normalize("TAPE ANCHOR PER-Q-CATH"), normalize("Surgical Tape")).relationship.id == "REL-001"
    repo.update("REL-001", changed_by="t", aliases=["TAPE ANCHOR PER-Q-CATH", "TAPE ANCHOR", "TAPE, SURGICAL", "TAPE, ANCHOR"])
    assert repo.store().lookup(normalize("TAPE, ANCHOR"), normalize("Surgical Tape")) is not None


def test_run_usage_is_reconstructable_after_edits(repo):
    repo.record_run_usage("run-abc", {"REL-001": 23, "REL-002": 0})
    repo.update("REL-001", changed_by="t", change_note="renamed", canonical="Surgical Tape (sterile)")
    repo.delete("REL-002", changed_by="t")
    used = repo.relationships_for_run("run-abc")
    by_id = {r.relationship.id: r for r in used}
    assert by_id["REL-001"].relationship.version == 1 and by_id["REL-001"].relationship.canonical == "Surgical Tape"
    assert by_id["REL-001"].used_count == 23
    assert by_id["REL-002"].relationship.canonical == "Measuring Tape" and by_id["REL-002"].used_count == 0
    assert repo.get("REL-001").version == 2 and repo.get("REL-001").canonical == "Surgical Tape (sterile)"


def test_usage_counts_aggregate_across_runs(repo):
    repo.record_run_usage("run-1", {"REL-001": 10})
    repo.record_run_usage("run-2", {"REL-001": 13, "REL-003": 2})
    counts = repo.usage_counts()
    assert counts["REL-001"] == 23 and counts["REL-003"] == 2 and counts.get("REL-002", 0) == 0


def test_list_filters(repo):
    repo.create(canonical="Family thing", aliases=["FAM"], scope="family:1295108", created_by="t")
    repo.create(canonical="Sku thing", aliases=["SKU"], scope="sku:1295108NS", created_by="t", doc_types=[DocType.BOM, DocType.DRAWING])
    assert {r.scope for r in repo.list(scope="family:1295108")} == {"family:1295108"}
    assert [r.canonical for r in repo.list(search="thing")] == ["Family thing", "Sku thing"]
    assert repo.list(search="sku thing")[0].doc_types == [DocType.BOM, DocType.DRAWING]
    repo.deactivate("REL-002", changed_by="t")
    assert "REL-002" not in {r.id for r in repo.list(active_only=True)}
    assert "REL-002" in {r.id for r in repo.list(active_only=False)}


def test_relationship_model_carries_version_fields():
    rel = Relationship(id="REL-1", canonical="x")
    assert rel.version == 1 and rel.updated_at is not None


def test_sync_defaults_adds_missing_and_refreshes_unedited_but_not_edited(repo):
    repo.delete("REL-002", changed_by="t", change_note="deleted on purpose")  # must NOT be resurrected
    repo.update("REL-001", changed_by="t", change_note="edited", aliases=["MY OWN ALIAS"])  # must NOT be touched
    repo.conn.execute("DELETE FROM relationships WHERE id = 'REL-009'")
    repo.conn.execute("DELETE FROM relationship_versions WHERE id = 'REL-009'")
    repo.conn.execute("UPDATE relationships SET aliases = '[\"OLD\"]' WHERE id = 'REL-003'")  # stale unedited default
    repo.conn.commit()
    added, refreshed = repo.sync_defaults(changed_by="sync")
    assert added == 1 and refreshed == 1
    assert repo.get("REL-009") is not None
    assert repo.get("REL-002") is None
    assert repo.get("REL-001").aliases == ["MY OWN ALIAS"]
    assert "MASK PROCEDURE" in repo.get("REL-003").aliases and repo.get("REL-003").version == 2

"""Automatic collection never requires visiting a learning page or approves truth."""

from fastapi.testclient import TestClient

from kaizen.api import app as module
from kaizen.api.app import RunCache, create_app
from kaizen.review.access import AccessStore
from kaizen.review.learning import LearningStore
from kaizen.workspace import Workspace
from tests.unit.test_quick_view import fixture

OWNER = 'owner@bd.com'
PASSWORD = 'automatic-collection-test'


def application(tmp_path):
    ws = Workspace(tmp_path / 'workspace')
    AccessStore(ws.db).bootstrap(OWNER, PASSWORD)
    app = create_app(ws)
    client = TestClient(app)
    assert client.post('/api/auth/signin', json={'email': OWNER, 'password': PASSWORD}).status_code == 200
    return ws, app, client


def test_new_run_collects_immediately_without_learning_page(tmp_path, monkeypatch):
    ws, app, client = application(tmp_path)
    source = tmp_path / 'source'
    source.mkdir()
    # This suite stubs extraction; upload validation is covered by the API regression suite.
    monkeypatch.setattr(module, 'document_sets', lambda root: [root])
    monkeypatch.setattr(module, 'run_folder', lambda *a, **k: fixture())
    response = client.post('/api/runs/from-path', json={'path': str(source), 'name': 'Automatic collection'})
    assert response.status_code == 200, response.text
    rid = response.json()['runs'][0]['run_id']
    learning = LearningStore(ws.db)
    assert learning.enrolled(rid)
    assert learning.split('SKU-A') == 'train'
    assert ws.db.conn.execute('SELECT COUNT(*) FROM learning_labels').fetchone()[0] == 0
    assert client.post(f'/api/runs/{rid}/decisions', json={'row_id': 'pair0', 'decision': 'ACCEPT', 'expected_revision': 0}).status_code == 200
    revision = learning.review.revision(rid, 'pair0')
    response = client.post(f'/api/runs/{rid}/finalize', json={'row_id': 'pair0', 'final_decision': 'ACCEPT', 'expected_revision': revision, 'confirm_self_approval': True})
    assert response.status_code == 200, response.text
    # Even approved ordinary work is observation data, never automatic verified truth.
    assert ws.db.conn.execute('SELECT COUNT(*) FROM review_events WHERE run_id=?', (rid,)).fetchone()[0] == 2
    assert ws.db.conn.execute('SELECT COUNT(*) FROM learning_labels').fetchone()[0] == 0
    assert ws.db.conn.execute('SELECT COUNT(*) FROM learning_jobs').fetchone()[0] == 0
    summary = client.get(f'/api/runs/{rid}/learning').json()
    assert summary['enabled'] and summary['collection_mode'] == 'automatic' and summary['setup_issue'] is None
    assert summary['review_events'] == 2 and summary['counts']['verified_train'] == 0
    ws.db.close()


def test_existing_owned_runs_backfill_once_on_startup(tmp_path):
    ws = Workspace(tmp_path / 'workspace')
    run = fixture()
    RunCache(ws).put(run)
    ws.db.conn.execute('UPDATE runs SET owner=? WHERE run_id=?', (OWNER, run.metadata.run_id))
    ws.db.conn.commit()
    learning = LearningStore(ws.db)
    assert not learning.enrolled(run.metadata.run_id)
    create_app(ws)
    assert learning.enrolled(run.metadata.run_id)
    before = list(ws.db.conn.execute('SELECT * FROM learning_partitions'))
    create_app(ws)
    assert list(ws.db.conn.execute('SELECT * FROM learning_partitions')) == before
    assert ws.db.conn.execute('SELECT COUNT(*) FROM learning_enrollments').fetchone()[0] == 1
    assert ws.db.conn.execute('SELECT COUNT(*) FROM run_shares').fetchone()[0] == 0
    assert ws.db.conn.execute('SELECT COUNT(*) FROM learning_labels').fetchone()[0] == 0
    ws.db.close()


def test_unknown_identity_does_not_block_review_or_fabricate_a_split(tmp_path, monkeypatch):
    ws, app, client = application(tmp_path)
    source = tmp_path / 'source'
    source.mkdir()
    run = fixture()
    run.groups[0].sku = 'UNKNOWN'
    for row in run.results:
        row.sku = 'UNKNOWN'
    # This suite stubs extraction; upload validation is covered by the API regression suite.
    monkeypatch.setattr(module, 'document_sets', lambda root: [root])
    monkeypatch.setattr(module, 'run_folder', lambda *a, **k: run)
    response = client.post('/api/runs/from-path', json={'path': str(source)})
    assert response.status_code == 200, response.text
    rid = response.json()['runs'][0]['run_id']
    assert client.post(f'/api/runs/{rid}/decisions', json={'row_id': 'pair0', 'decision': 'NEEDS_MORE_INFORMATION', 'expected_revision': 0}).status_code == 200
    summary = client.get(f'/api/runs/{rid}/learning').json()
    assert summary['enabled'] is False and summary['collection_mode'] == 'automatic'
    assert 'product identities' in summary['setup_issue']
    assert summary['review_events'] == 1
    observations = client.get(f'/api/runs/{rid}/learning/observations.json')
    assert observations.status_code == 200 and len(observations.json()['rows']) == 1
    assert 'not verified training labels' in observations.json()['purpose']
    assert 'no-store' in observations.headers['cache-control']
    assert ws.db.conn.execute('SELECT COUNT(*) FROM learning_partitions').fetchone()[0] == 0
    ws.db.close()


def test_startup_skips_deleted_unowned_and_missing_runs(tmp_path):
    ws = Workspace(tmp_path / 'workspace')
    cache = RunCache(ws)
    for rid in ('deleted', 'unowned', 'missing'):
        run = fixture()
        run.metadata.run_id = rid
        path = cache.put(run)
        if rid != 'unowned':
            ws.db.conn.execute('UPDATE runs SET owner=? WHERE run_id=?', (OWNER, rid))
        if rid == 'deleted':
            ws.db.conn.execute("UPDATE runs SET deleted_at='2026-10-17' WHERE run_id=?", (rid,))
        if rid == 'missing':
            path.unlink()
    ws.db.conn.commit()
    create_app(ws)
    assert ws.db.conn.execute('SELECT COUNT(*) FROM learning_enrollments').fetchone()[0] == 0
    ws.db.close()

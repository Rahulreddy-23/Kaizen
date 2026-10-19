"""Erasure must reclaim private files without crossing ownership or source boundaries."""
import shutil
from pathlib import Path

import pytest

from kaizen.api.app import RunCache, create_app
from kaizen.review.access import AccessStore
from kaizen.review.sessions import UserStore
from kaizen.storage.purge import RUN_TABLES
from tests.integration.test_api_regressions import EMAIL, PASSWORD, upload
from tests.integration.test_api_regressions import env as api_env


@pytest.fixture
def env(tmp_path):
    yield from api_env.__wrapped__(tmp_path)


def purge(client, rid):
    return client.request('DELETE', f'/api/runs/{rid}/permanent', json={'confirmation': rid})


def test_upload_purge_frees_files_and_run_scoped_data_preserving_copies(env):
    ws, client, _, source = env
    terminology_count = len(ws.repository.list())
    created = upload(client, source).json()
    rid = created['run_id']
    record = ws.runs.get(rid)
    run_dir, uploads = ws.runs_dir / rid, Path(record['input_root'])
    (run_dir / 'learning').mkdir()
    (run_dir / 'learning' / 'candidate.json').write_text('private candidate')
    (run_dir / 'review.xlsx').write_bytes(b'private export')
    copied = client.post(f'/api/runs/{rid}/copy').json()['run_id']
    ws.db.conn.execute('INSERT INTO review_events (run_id,row_id,payload) VALUES (?,?,?)', (rid, 'test', '{"comment":"private review"}'))
    ws.db.conn.execute('INSERT INTO learning_evaluations VALUES (?,?,?,?,?)', ('report', rid, EMAIL, 'now', '{}'))
    ws.db.conn.commit()
    assert sum(p.stat().st_size for p in uploads.rglob('*') if p.is_file()) > 0
    assert client.delete(f'/api/runs/{rid}').status_code == 200
    assert uploads.exists() and run_dir.exists()  # Soft deletion does not reclaim storage.
    response = purge(client, rid)
    assert response.status_code == 200, response.text
    assert response.json() == {'run_id': rid, 'deleted': True, 'cleanup_pending': False, 'files_retained': False}
    assert not run_dir.exists() and not uploads.exists()
    assert ws.runs.get(rid, include_deleted=True) is None
    for table in RUN_TABLES:
        assert ws.db.conn.execute(f'SELECT count(*) FROM {table} WHERE run_id=?', (rid,)).fetchone()[0] == 0
    assert ws.db.conn.execute('SELECT count(*) FROM run_file_cleanup').fetchone()[0] == 0
    assert client.get(f'/api/runs/{rid}').status_code == 404
    assert client.post(f'/api/runs/{rid}/restore').status_code == 404
    assert purge(client, rid).status_code == 404
    assert source.is_dir() and len(list(source.glob('*.pdf'))) == 3
    assert client.get(f'/api/runs/{copied}').status_code == 200
    copy_sources = list((ws.runs_dir / copied / 'files').rglob('*.pdf'))
    assert len(copy_sources) == 3 and all(p.read_bytes().startswith(b'%PDF') for p in copy_sources)
    assert client.get('/api/runs?deleted=true').json() == []
    assert len(ws.repository.list()) == terminology_count


def test_database_failure_keeps_run_and_files_recoverable(env, monkeypatch):
    ws, client, run, source = env
    rid = run.metadata.run_id
    client.delete(f'/api/runs/{rid}')
    def fail(*_args):
        raise RuntimeError('Simulated database failure')
    monkeypatch.setattr(ws.db, 'audit', fail)
    with pytest.raises(RuntimeError, match='Simulated database failure'):
        purge(client, rid)
    assert ws.runs.get(rid, include_deleted=True)['deleted_at']
    assert (ws.runs_dir / rid / 'run.json').exists() and source.exists()
    assert ws.db.conn.execute('SELECT count(*) FROM run_file_cleanup').fetchone()[0] == 0


def test_purge_requires_deleted_state_confirmation_and_owner_even_for_admin(env):
    ws, client, run, source = env
    rid = run.metadata.run_id
    assert purge(client, rid).status_code == 409
    assert client.delete(f'/api/runs/{rid}').status_code == 200
    assert client.request('DELETE', f'/api/runs/{rid}/permanent', json={'confirmation': 'wrong'}).status_code == 400
    assert client.request('DELETE', f'/api/runs/{rid}/permanent').status_code == 422
    UserStore(ws.db).create('other-admin@bd.com', PASSWORD)
    access = AccessStore(ws.db)
    access.register('other-admin@bd.com')
    access.update('other-admin@bd.com', EMAIL, 'approved', True)
    assert client.post('/api/auth/signin', json={'email': 'other-admin@bd.com', 'password': PASSWORD}).status_code == 200
    assert purge(client, rid).status_code == 404
    assert ws.runs.get(rid, include_deleted=True)
    client.post('/api/auth/signin', json={'email': EMAIL, 'password': PASSWORD})
    assert purge(client, rid).status_code == 200
    assert source.exists()  # Local originals are never managed uploads.


def test_shared_uploaded_sources_survive_until_the_last_run_is_purged(env):
    ws, client, _, source = env
    rid = upload(client, source).json()['run_id']
    cache = RunCache(ws)
    shared = cache.get(rid).model_copy(deep=True)
    shared.metadata.run_id = 'legacy-shared'
    cache.put(shared)
    ws.db.conn.execute('UPDATE runs SET owner=? WHERE run_id=?', (EMAIL, shared.metadata.run_id))
    ws.db.conn.commit()
    uploads = Path(ws.runs.get(rid)['input_root'])
    client.delete(f'/api/runs/{shared.metadata.run_id}')  # Also protect soft-deleted references.
    client.delete(f'/api/runs/{rid}')
    assert purge(client, rid).status_code == 200
    assert uploads.exists()
    assert purge(client, shared.metadata.run_id).status_code == 200
    assert not uploads.exists()


def test_file_cleanup_failure_is_durable_and_resumed_on_startup(env, monkeypatch):
    ws, client, _, source = env
    rid = upload(client, source).json()['run_id']
    uploads = Path(ws.runs.get(rid)['input_root'])
    client.delete(f'/api/runs/{rid}')
    with monkeypatch.context() as patch:
        patch.setattr(shutil, 'rmtree', lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError('Storage busy')))
        response = purge(client, rid)
    assert response.status_code == 200 and response.json()['cleanup_pending'] is True
    assert ws.runs.get(rid, include_deleted=True) is None
    assert ws.db.conn.execute('SELECT count(*) FROM run_file_cleanup WHERE run_id=?', (rid,)).fetchone()[0] == 1
    create_app(ws)
    assert not uploads.exists() and not (ws.runs_dir / rid).exists()
    assert ws.db.conn.execute('SELECT count(*) FROM run_file_cleanup').fetchone()[0] == 0


def test_cleanup_retry_rechecks_new_source_references(env, monkeypatch):
    ws, client, _, source = env
    rid = upload(client, source).json()['run_id']
    cache = RunCache(ws)
    reused = cache.get(rid).model_copy(deep=True)
    reused.metadata.run_id = 'new-reference-after-storage-error'
    uploads = Path(ws.runs.get(rid)['input_root'])
    client.delete(f'/api/runs/{rid}')
    with monkeypatch.context() as patch:
        patch.setattr(shutil, 'rmtree', lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError('Storage busy')))
        assert purge(client, rid).json()['cleanup_pending'] is True
    cache.put(reused)
    ws.db.conn.execute('UPDATE runs SET owner=? WHERE run_id=?', (EMAIL, reused.metadata.run_id))
    ws.db.conn.commit()
    create_app(ws)
    assert uploads.exists()
    assert ws.db.conn.execute('SELECT count(*) FROM run_file_cleanup').fetchone()[0] == 1


def test_purge_cannot_follow_run_directory_symlinks(env):
    ws, client, run, source = env
    rid = run.metadata.run_id
    client.delete(f'/api/runs/{rid}')
    shutil.rmtree(ws.runs_dir / rid)
    (ws.runs_dir / rid).symlink_to(source, target_is_directory=True)
    assert purge(client, rid).status_code == 200
    assert len(list(source.glob('*.pdf'))) == 3


def test_broken_other_run_preserves_uncertain_shared_sources(env):
    ws, client, run, source = env
    rid = upload(client, source).json()['run_id']
    uploads = Path(ws.runs.get(rid)['input_root'])
    Path(ws.runs.get(run.metadata.run_id)['json_path']).write_text('unreadable legacy run')
    client.delete(f'/api/runs/{rid}')
    assert purge(client, rid).status_code == 200
    assert uploads.exists()


def test_inflight_learning_blocks_purge_without_erasing_evidence(env, monkeypatch):
    import threading

    ws, client, run, _ = env
    rid = run.metadata.run_id
    from kaizen.api import app as module
    # Simulate a startup-resumed job, outside an HTTP request's run guard.
    ws.db.conn.execute("INSERT INTO learning_jobs VALUES (?,1,0,'queued',?,'','now')", (rid, EMAIL))
    ws.db.conn.commit()
    started, release = threading.Event(), threading.Event()
    def shadow(*_args):
        started.set()
        assert release.wait(10)
    monkeypatch.setattr(module, 'shadow_evaluate', shadow)
    from fastapi.testclient import TestClient
    with TestClient(create_app(ws)) as other:
        other.post('/api/auth/signin', json={'email': EMAIL, 'password': PASSWORD})
        assert started.wait(10)
        other.delete(f'/api/runs/{rid}')
        try:
            response = purge(other, rid)
            assert response.status_code == 409
            assert (ws.runs_dir / rid / 'run.json').exists()
        finally:
            release.set()

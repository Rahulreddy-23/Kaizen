"""Reruns reprocess a run's stored sources and are offered as versions of the original run."""
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest

from kaizen.api import app as api_module
from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.review.access import AccessStore
from tests.integration.test_api_regressions import EMAIL, upload
from tests.integration.test_api_regressions import env as api_env

OTHER = 'colleague@bd.com'


@pytest.fixture
def env(tmp_path):
    yield from api_env.__wrapped__(tmp_path)


def test_rerun_creates_numbered_versions_listed_under_the_original(env):
    ws, client, _, source = env
    created = upload(client, source).json()
    rid = created['run_id']

    first = client.post(f'/api/runs/{rid}/rerun')
    assert first.status_code == 200, first.text
    first = first.json()
    assert first['run_id'] != rid and first['rerun_of'] == rid and first['rerun_number'] == 1
    assert first['owner'] == EMAIL and first['permission'] == 'owner'
    assert first['name'].endswith('· Rerun 1')
    assert first['rows'] == created['rows']
    assert client.patch(f'/api/runs/{rid}', json={'name': 'A' * 120}).status_code == 200
    # Rerunning a rerun still numbers under the original and reuses the original's stored sources.
    second = client.post(f"/api/runs/{first['run_id']}/rerun").json()
    assert second['rerun_of'] == rid and second['rerun_number'] == 2
    assert len(second['name']) == 120 and second['name'].endswith('· Rerun 2')
    assert ws.runs.get(second['run_id'])['input_root'] == ws.runs.get(rid)['input_root']

    versions = client.get(f'/api/runs/{rid}/versions').json()
    assert [(v['run_id'], v['rerun_number']) for v in versions] == [(rid, 0), (first['run_id'], 1), (second['run_id'], 2)]
    assert client.get(f"/api/runs/{second['run_id']}/versions").json() == versions

    listed = {r['run_id']: r for r in client.get('/api/runs').json()}
    assert rid in listed and first['run_id'] not in listed and second['run_id'] not in listed
    assert listed[rid]['reruns'] == 2

    for detail in ('summary', 'complete', 'bcc'):
        response = client.get(f"/api/runs/{first['run_id']}/export.xlsx", params={'detail': detail})
        assert response.status_code == 200, (detail, response.text)
        assert response.content.startswith(b'PK')


def test_rerun_streams_progress(env):
    _, client, _, source = env
    rid = upload(client, source).json()['run_id']
    response = client.post(f'/api/runs/{rid}/rerun', params={'stream': 'true'})
    assert response.status_code == 200
    lines = [line for line in response.text.splitlines() if line.strip()]
    assert '"type": "result"' in lines[-1] and '"rerun_number": 1' in lines[-1]


def test_reruns_follow_the_original_access_and_deletion(env):
    ws, client, _, source = env
    rid = upload(client, source).json()['run_id']
    rerun = client.post(f'/api/runs/{rid}/rerun').json()['run_id']
    access = AccessStore(ws.db)
    assert access.permission(rerun, OTHER) is None
    ws.db.conn.execute("INSERT INTO run_shares VALUES (?,?,?,?,?)", (rid, OTHER, 'view', EMAIL, 'now'))
    ws.db.conn.commit()
    assert access.permission(rerun, OTHER) == 'view'
    assert client.get(f'/api/runs/{rerun}/sharing').json() == client.get(f'/api/runs/{rid}/sharing').json()
    assert client.put(f'/api/runs/{rerun}/sharing', json={'email': OTHER, 'permission': 'edit'}).status_code == 400
    assert client.delete(f'/api/runs/{rerun}').status_code == 400

    assert client.delete(f'/api/runs/{rid}').status_code == 200
    assert client.get('/api/runs', params={'deleted': 'true'}).json()[0]['reruns'] == 1
    assert client.get(f'/api/runs/{rerun}').status_code == 404
    assert client.post(f'/api/runs/{rid}/restore').status_code == 200
    assert client.get(f'/api/runs/{rerun}').status_code == 200

    uploads = Path(ws.runs.get(rid)['input_root'])
    client.delete(f'/api/runs/{rid}')
    response = client.request('DELETE', f'/api/runs/{rid}/permanent', json={'confirmation': rid})
    assert response.status_code == 200, response.text
    assert response.json()['cleanup_pending'] is False
    assert ws.runs.get(rerun, include_deleted=True) is None
    assert not (ws.runs_dir / rerun).exists() and not uploads.exists()


def test_purge_waits_for_a_rerun_in_progress_and_deleted_original_blocks_save(env, monkeypatch):
    ws, client, _, source = env
    rid = upload(client, source).json()['run_id']
    version_id = client.post(f'/api/runs/{rid}/rerun').json()['run_id']
    started, release = Event(), Event()
    run_folder = api_module.run_folder

    def delayed(*args, **kwargs):
        started.set()
        assert release.wait(10)
        return run_folder(*args, **kwargs)

    monkeypatch.setattr(api_module, 'run_folder', delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        rerun = pool.submit(client.post, f'/api/runs/{version_id}/rerun')
        try:
            assert started.wait(10)
            assert client.delete(f'/api/runs/{rid}').status_code == 200
            assert client.request('DELETE', f'/api/runs/{rid}/permanent', json={'confirmation': rid}).status_code == 409
        finally:
            release.set()
        assert rerun.result(timeout=10).status_code == 404

    assert set(ws.runs.version_ids(rid)) == {rid, version_id}
    assert client.request('DELETE', f'/api/runs/{rid}/permanent', json={'confirmation': rid}).status_code == 200


def test_rerun_reads_the_folder_again_from_scratch(env):
    """A changed document in the run's folder is picked up: nothing from the earlier run is reused."""
    ws, client, _, source = env
    created = upload(client, source).json()
    rid = created['run_id']
    kit = next(Path(ws.runs.get(rid)['input_root']).rglob('bom.pdf')).parent
    render_bom_pdf(BomSpec(parent_item='1295108NS', parent_description='KIT', rows=[
        BomRowSpec(item='2260001', description='END CAP', qty_per='2'),
        BomRowSpec(item='2330001', description='TOURNIQUET', qty_per='1'),
    ]), kit / 'bom.pdf')
    rerun = client.post(f'/api/runs/{rid}/rerun')
    assert rerun.status_code == 200, rerun.text
    rows = client.get(f"/api/runs/{rerun.json()['run_id']}/results", params={'limit': 500}).json()
    text = str(rows)
    assert 'TOURNIQUET' in text
    assert 'TOURNIQUET' not in str(client.get(f'/api/runs/{rid}/results', params={'limit': 500}).json())


def test_rerun_applies_the_upload_rules_to_the_folder(env):
    ws, client, _, source = env
    rid = upload(client, source).json()['run_id']
    kit = next(Path(ws.runs.get(rid)['input_root']).rglob('label.pdf')).parent
    (kit / 'label.pdf').unlink()
    response = client.post(f'/api/runs/{rid}/rerun')
    assert response.status_code == 400
    assert 'exactly one BOM, one label and one drawing' in response.json()['detail']
    for file in kit.iterdir():
        file.unlink()
    response = client.post(f'/api/runs/{rid}/rerun')
    assert response.status_code == 400
    assert 'No PDF, XLSX, XLSM or CSV documents' in response.json()['detail']


def test_rerun_cannot_fill_missing_kit_documents_from_a_nested_folder_or_link(env):
    ws, client, _, source = env
    rid = upload(client, source).json()['run_id']
    label = next(Path(ws.runs.get(rid)['input_root']).rglob('label.pdf'))
    nested = label.parent / 'other-kit'
    nested.mkdir()
    shutil.move(label, nested / label.name)
    response = client.post(f'/api/runs/{rid}/rerun')
    assert response.status_code == 400
    assert 'exactly one BOM, one label and one drawing' in response.json()['detail']
    label.symlink_to(source / 'label.pdf')
    response = client.post(f'/api/runs/{rid}/rerun')
    assert response.status_code == 400
    assert 'file linked outside' in response.json()['detail']


def test_rerun_of_a_demo_dataset_rescans_every_kit(env):
    _, client, _, _ = env
    demo = client.post('/api/demo/load').json()
    rerun = client.post(f"/api/runs/{demo['run_id']}/rerun")
    assert rerun.status_code == 200, rerun.text
    assert rerun.json()['skus'] == demo['skus'] and rerun.json()['rows'] == demo['rows']


def test_rerun_of_an_independent_copy(env):
    _, client, _, source = env
    rid = upload(client, source).json()['run_id']
    copied = client.post(f'/api/runs/{rid}/copy').json()['run_id']
    rerun = client.post(f'/api/runs/{copied}/rerun')
    assert rerun.status_code == 200, rerun.text
    assert rerun.json()['rerun_of'] == copied


def test_view_only_users_cannot_rerun(env):
    ws, client, _, source = env
    rid = upload(client, source).json()['run_id']
    ws.db.conn.execute('UPDATE runs SET owner=? WHERE run_id=?', (OTHER, rid))
    ws.db.conn.execute("INSERT INTO run_shares VALUES (?,?,?,?,?)", (rid, EMAIL, 'view', OTHER, 'now'))
    ws.db.conn.commit()
    assert client.post(f'/api/runs/{rid}/rerun').status_code == 403

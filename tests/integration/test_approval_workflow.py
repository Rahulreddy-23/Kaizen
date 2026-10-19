"""Counts and filtered lists must agree through every persisted review transition."""
import pytest

from kaizen.models import Classification
from kaizen.pipeline import save_run
from tests.integration.test_api_regressions import EMAIL, PASSWORD, review_row
from tests.integration.test_api_regressions import env as api_env


@pytest.fixture
def env(tmp_path):
    yield from api_env.__wrapped__(tmp_path)


def assert_counts(client, rid):
    base = f'/api/runs/{rid}'
    summary = client.get(base).json()
    progress = summary['review_progress']
    approved = client.get(f'{base}/results', params={'state': 'FINALIZED', 'limit': 5000}).json()
    pending = client.get(f'{base}/results', params={'needs_validation': True, 'limit': 5000}).json()
    assert progress['approved'] == approved['total'] == summary['state_counts']['FINALIZED']
    assert progress['pending'] == pending['total']
    listed = next(r for r in client.get('/api/runs').json() if r['run_id'] == rid)
    assert listed['summary']['review_progress'] == progress
    return progress, approved['rows']


@pytest.mark.parametrize(('kind', 'classification'), [
    ('ACCEPT', None), ('CONFIRM_DISCREPANCY', None), ('NEEDS_MORE_INFORMATION', None),
    ('OVERRIDE', 'EXACT'), ('OVERRIDE', 'EQUIVALENT'), ('OVERRIDE', 'POTENTIAL'),
    ('OVERRIDE', 'MISMATCH'), ('OVERRIDE', 'MISSING'),
])
def test_saved_decision_approval_repeated_submit_and_reopen_counts(env, kind, classification):
    _, client, run, _ = env
    rid = run.metadata.run_id
    row = next(r for r in run.results if r.role == 'item' and r.requires_validation and r.discrepancies)
    base = f'/api/runs/{rid}'
    before, _ = assert_counts(client, rid)
    review_row(client, rid, row.row_id, kind, classification)
    saved, _ = assert_counts(client, rid)
    assert saved['approved'] == 0 and saved['awaiting_approval'] == before['awaiting_approval'] + 1
    detail = client.get(f'{base}/results/{row.row_id}').json()
    payload = {'row_id': row.row_id, 'final_decision': kind, 'expected_revision': detail['revision'], 'confirm_self_approval': True}
    assert client.post(f'{base}/finalize', json=payload).status_code == 200
    approved, rows = assert_counts(client, rid)
    assert approved['approved'] == 1 and rows[0]['row_id'] == row.row_id
    assert approved['pending'] == before['pending'] - (kind != 'NEEDS_MORE_INFORMATION')
    if kind == 'OVERRIDE' and classification in ('EXACT', 'EQUIVALENT'):
        assert rows[0]['unresolved'] is False
    else:
        assert rows[0]['unresolved'] is True
    assert client.post(f'{base}/finalize', json=payload).status_code in (400, 409)
    assert assert_counts(client, rid)[0]['approved'] == 1
    review_row(client, rid, row.row_id, 'NEEDS_MORE_INFORMATION')
    reopened, rows = assert_counts(client, rid)
    assert reopened['approved'] == 0 and not rows
    assert reopened['needs_information'] >= 1


def make_bulk_case(ws, run):
    paired = next(r for r in run.results if r.role == 'item' and r.source_a and r.source_b)
    clean = paired.model_copy(deep=True, update={'classification': Classification.EXACT, 'requires_validation': False, 'discrepancies': []})
    run.results = [clean.model_copy(deep=True, update={'row_id': name}) for name in ('new', 'accepted', 'protected', 'already-approved')]
    run.results.extend([
        clean.model_copy(deep=True, update={'row_id': 'flagged', 'requires_validation': True}),
        clean.model_copy(deep=True, update={'row_id': 'unpaired', 'source_b': None}),
        clean.model_copy(deep=True, update={'row_id': 'header', 'role': 'header'}),
        clean.model_copy(deep=True, update={'row_id': 'exempt', 'role': 'exempt'}),
    ])
    save_run(run, ws.runs.get(run.metadata.run_id)['json_path'])


def test_bulk_accept_is_review_only_and_bulk_approval_is_safe_and_counted(env):
    ws, client, run, _ = env
    make_bulk_case(ws, run)
    rid = run.metadata.run_id
    base = f'/api/runs/{rid}'
    review_row(client, rid, 'accepted', 'ACCEPT')
    review_row(client, rid, 'protected', 'CONFIRM_DISCREPANCY')
    review_row(client, rid, 'already-approved', 'ACCEPT', approve=True)
    preview = client.get(f'{base}/bulk-review').json()
    assert preview['accept_count'] == 1 and preview['approve_count'] == 2
    assert client.post(f'{base}/bulk-approve', json={'expected_revision': preview['revision']}).status_code == 400
    assert client.post(f'{base}/bulk-accept', json={}).json()['accepted'] == 1
    reviewed, _ = assert_counts(client, rid)
    assert reviewed['approved'] == 1
    assert client.post(f'{base}/bulk-approve', json={'expected_revision': preview['revision'], 'confirm_self_approval': True}).status_code == 409
    preview = client.get(f'{base}/bulk-review').json()
    payload = {'expected_revision': preview['revision'], 'confirm_self_approval': True}
    assert client.post(f'{base}/bulk-approve', json=payload).json() == {'approved': 2}
    progress, rows = assert_counts(client, rid)
    assert progress['approved'] == 3
    assert {r['row_id'] for r in rows} == {'new', 'accepted', 'already-approved'}
    assert all(r['final']['self_approved'] for r in rows)
    assert all(not r['pending_review'] for r in rows)
    assert client.post(f'{base}/bulk-approve', json=payload).status_code == 409
    empty = client.get(f'{base}/bulk-review').json()
    assert empty['approve_count'] == empty['accept_count'] == 0
    assert client.post(f'{base}/bulk-approve', json={'expected_revision': empty['revision'], 'confirm_self_approval': True}).json()['approved'] == 0
    assert assert_counts(client, rid)[0]['approved'] == 3
    from fastapi.testclient import TestClient

    from kaizen.api.app import create_app
    restarted = TestClient(create_app(ws))
    assert restarted.post('/api/auth/signin', json={'email': EMAIL, 'password': PASSWORD}).status_code == 200
    assert assert_counts(restarted, rid)[0]['approved'] == 3
    for row_id in ('flagged', 'unpaired', 'header', 'exempt'):
        detail = client.get(f'{base}/results/{row_id}').json()
        assert not detail['final'] and not any(detail['decisions'].values())
    assert client.get(f'{base}/results/protected').json()['decisions']['1']['decision'] == 'CONFIRM_DISCREPANCY'


def test_bulk_preview_detects_intervening_edits_and_cannot_partially_approve(env):
    ws, client, run, _ = env
    make_bulk_case(ws, run)
    rid = run.metadata.run_id
    base = f'/api/runs/{rid}'
    preview = client.get(f'{base}/bulk-review').json()
    review_row(client, rid, 'new', 'NEEDS_MORE_INFORMATION')
    response = client.post(f'{base}/bulk-approve', json={'expected_revision': preview['revision'], 'confirm_self_approval': True})
    assert response.status_code == 409
    assert assert_counts(client, rid)[0]['approved'] == 0
    assert client.post(f'{base}/bulk-approve', json={'expected_revision': preview['revision'], 'confirm_self_approval': 'true'}).status_code == 422


def test_bulk_approval_transaction_rolls_back_on_a_midway_failure(env, monkeypatch):
    from kaizen.review.collaborative import CollaborativeReviewStore
    ws, client, run, _ = env
    make_bulk_case(ws, run)
    rid = run.metadata.run_id
    base = f'/api/runs/{rid}'
    preview = client.get(f'{base}/bulk-review').json()
    original = CollaborativeReviewStore.approve
    calls = []
    def fail_second(self, *args):
        calls.append(args[1])
        if len(calls) == 2:
            raise ValueError('Simulated approval failure')
        return original(self, *args)
    monkeypatch.setattr(CollaborativeReviewStore, 'approve', fail_second)
    response = client.post(f'{base}/bulk-approve', json={'expected_revision': preview['revision'], 'confirm_self_approval': True})
    assert response.status_code == 400 and len(calls) == 2
    assert assert_counts(client, rid)[0]['approved'] == 0
    assert ws.db.conn.execute('SELECT count(*) FROM decisions WHERE run_id=?', (rid,)).fetchone()[0] == 0

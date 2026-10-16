"""Invite-only access and account-scoped terminology over the real HTTP boundary."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from kaizen.api.app import create_app
from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.review.access import AccessStore
from kaizen.review.sessions import UserStore
from kaizen.terminology.catalog import TerminologyCatalog
from kaizen.workspace import Workspace

ADMIN, ALICE, BOB = 'admin@bd.com', 'alice@bd.com', 'bob@bd.com'
PW = 'invite-only-password-2026'


@pytest.fixture
def env(tmp_path):
    ws = Workspace(tmp_path / 'ws')
    AccessStore(ws.db).bootstrap(ADMIN, PW)
    app = create_app(ws)
    admin = TestClient(app)
    assert admin.post('/api/auth/signin', json={'email': ADMIN, 'password': PW}).status_code == 200
    yield ws, admin, app
    ws.db.close()


def invite(admin, email):
    response = admin.post('/api/admin/invitations', json={'email': email})
    assert response.status_code == 200, response.text
    return response.json()


def join(admin, app, email):
    code = invite(admin, email)['code']
    client = TestClient(app)
    response = client.post('/api/auth/signup', json={'email': email, 'password': PW, 'invitation': code})
    assert response.status_code == 200, response.text
    assert client.post('/api/auth/signin', json={'email': email, 'password': PW}).status_code == 200
    return client


def approve(client, canonical='Shared closure', alias='SPECIAL END CAP'):
    response = client.post('/api/terminology', json={'canonical': canonical, 'aliases': [alias], 'created_by': ADMIN, 'by': ADMIN})
    assert response.status_code == 200, response.text
    return response.json()


def choose(client, rels, selected=True):
    return client.put('/api/terminology/selections', json={'entries': [{'id': r['id'], 'version': r['version']} for r in rels], 'selected': selected})


def test_registration_requires_private_email_bound_code(env):
    ws, admin, app = env
    anonymous = TestClient(app)
    body = {'email': ALICE, 'password': PW}
    assert anonymous.post('/api/auth/signup', json=body).status_code == 403
    assert not UserStore(ws.db).exists(ALICE)
    invitation = invite(admin, ALICE)
    wrong = anonymous.post('/api/auth/signup', json=body | {'email': BOB, 'invitation': invitation['code']})
    assert wrong.status_code == 403
    assert not UserStore(ws.db).exists(BOB)
    body['invitation'] = invitation['code']
    assert anonymous.post('/api/auth/signup', json=body | {'password': 'short'}).status_code == 400
    assert anonymous.post('/api/auth/signup', json=body).status_code == 200
    assert anonymous.post('/api/auth/signup', json=body).status_code == 403
    assert anonymous.post('/api/auth/signin', json={'email': ALICE, 'password': PW}).status_code == 200
    listing = admin.get('/api/admin/invitations').json()
    assert listing[0]['consumed_at'] and 'code' not in listing[0] and 'token_hash' not in listing[0]
    stored = ws.db.conn.execute('SELECT token_hash FROM account_invitations').fetchone()[0]
    assert stored != invitation['code'] and len(stored) == 64
    assert invitation['code'] not in str([dict(r) for r in ws.db.conn.execute('SELECT * FROM audit')])
    assert anonymous.get('/api/admin/invitations').status_code == 403
    assert anonymous.post('/api/admin/invitations', json={'email': BOB}).status_code == 403


@pytest.mark.parametrize('reason', ['expired', 'revoked', 'superseded', 'inviter_revoked'])
def test_inactive_invitations_never_grant_access(env, reason):
    ws, admin, app = env
    invitation = invite(admin, ALICE)
    if reason == 'expired':
        ws.db.conn.execute('UPDATE account_invitations SET expires_at=?', ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),))
        ws.db.conn.commit()
    elif reason == 'revoked':
        assert admin.delete(f'/api/admin/invitations/{invitation["id"]}').status_code == 200
    elif reason == 'superseded':
        invite(admin, ALICE)
    else:
        other = join(admin, app, 'second-admin@bd.com')
        assert admin.patch('/api/admin/users/second-admin@bd.com', json={'is_admin': True}).status_code == 200
        assert other.patch(f'/api/admin/users/{ADMIN}', json={'status': 'rejected'}).status_code == 200
    response = TestClient(app).post('/api/auth/signup', json={'email': ALICE, 'password': PW, 'invitation': invitation['code']})
    assert response.status_code == 403
    assert not UserStore(ws.db).exists(ALICE)


def test_concurrent_registration_consumes_once(env):
    ws, admin, app = env
    body = {'email': ALICE, 'password': PW, 'invitation': invite(admin, ALICE)['code']}
    def register(_):
        return TestClient(app).post('/api/auth/signup', json=body).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(register, range(2))) == [200, 403]
    assert len([r for r in ws.db.conn.execute('SELECT * FROM users WHERE email=?', (ALICE,))]) == 1


def test_password_and_provider_membership_never_auto_approve(env):
    ws, admin, app = env
    UserStore(ws.db).create(ALICE, PW)
    AccessStore(ws.db).register(ALICE)
    client = TestClient(app)
    assert client.post('/api/auth/signin', json={'email': ALICE, 'password': PW}).status_code == 403
    assert AccessStore(ws.db).profile(ALICE)['status'] == 'pending'
    assert client.get('/api/terminology').status_code == 401
    bob = join(admin, app, BOB)
    assert admin.patch(f'/api/admin/users/{BOB}', json={'status': 'rejected'}).status_code == 200
    assert bob.get('/api/terminology').status_code == 401
    assert bob.post('/api/auth/signin', json={'email': BOB, 'password': PW}).status_code == 403
    assert admin.post('/api/admin/invitations', json={'email': BOB}).status_code == 400


def test_approved_terms_are_attributed_and_optional_for_other_reviewers(env):
    ws, admin, app = env
    alice, bob = join(admin, app, ALICE), join(admin, app, BOB)
    first, second = approve(alice), approve(alice, 'Second term', 'SECOND SOURCE')
    catalog = bob.get('/api/terminology').json()
    entry = next(r for r in catalog if r['id'] == first['id'])
    assert entry['approved_by'] == ALICE and entry['approved_at']
    assert not entry['enabled_version']
    own = next(r for r in alice.get('/api/terminology').json() if r['id'] == first['id'])
    assert own['enabled_version'] == own['selected_version'] == 1
    assert choose(bob, [first]).status_code == 200
    store = TerminologyCatalog(ws.repository).store(BOB)
    assert store.get(first['id']) is not None and store.get(second['id']) is None
    assert choose(bob, [first, second]).status_code == 200
    assert choose(bob, [first], False).status_code == 200
    assert TerminologyCatalog(ws.repository).store(BOB).get(first['id']) is None
    assert TerminologyCatalog(ws.repository).store(ALICE).get(first['id']) is not None
    assert alice.put(f'/api/terminology/{first["id"]}', json={'canonical': 'Overwrite'}).status_code == 403
    assert alice.post(f'/api/terminology/{first["id"]}/deactivate').status_code == 403


def test_version_changes_require_reselection_and_batches_are_atomic(env):
    ws, admin, app = env
    alice, bob = join(admin, app, ALICE), join(admin, app, BOB)
    first, second = approve(alice), approve(alice, 'Other term', 'OTHER SOURCE')
    assert choose(bob, [first]).status_code == 200
    newer = admin.put(f'/api/terminology/{first["id"]}', json={'canonical': 'Revised closure', 'aliases': ['REVISED SOURCE']}).json()
    assert newer['version'] == 2
    assert TerminologyCatalog(ws.repository).store(BOB).get(first['id']).canonical == first['canonical']
    visible = bob.get(f'/api/terminology/{first["id"]}').json()
    assert visible['enabled_definition']['canonical'] == first['canonical']
    assert choose(bob, [second, first]).status_code == 409
    assert TerminologyCatalog(ws.repository).store(BOB).get(second['id']) is None
    assert choose(bob, [newer]).status_code == 200
    assert TerminologyCatalog(ws.repository).store(BOB).get(first['id']).version == 2
    assert admin.post(f'/api/terminology/{first["id"]}/deactivate').status_code == 200
    assert TerminologyCatalog(ws.repository).store(BOB).get(first['id']) is None
    assert choose(bob, [newer]).status_code == 409
    assert choose(bob, [second, second]).status_code == 409
    assert admin.post(f'/api/terminology/{second["id"]}/deactivate').status_code == 200
    inactive = bob.get(f'/api/terminology/{second["id"]}').json()
    assert inactive['approved_by'] == ALICE, 'Deactivation must not claim the moderator approved the equivalence.'
    assert choose(bob, [{'id': 'missing', 'version': 1}]).status_code == 404


def test_account_choices_reach_new_uploads_and_survive_restart(env, tmp_path):
    ws, admin, app = env
    alice, bob = join(admin, app, ALICE), join(admin, app, BOB)
    rel = approve(alice)
    source = tmp_path / 'input'
    render_bom_pdf(BomSpec(parent_item='1295108NS', parent_description='KIT', rows=[BomRowSpec(item='2260001', description='SPECIAL END CAP', qty_per='1')]), source / 'bom.pdf')
    render_label_pdf(LabelSpec(ref='1295108', product_name='KIT', contents=['1 Each - Shared closure']), source / 'label.pdf')
    def upload():
        response = bob.post('/api/runs/upload', files=[('files', (p.name, p.read_bytes(), 'application/pdf')) for p in source.glob('*.pdf')])
        assert response.status_code == 200, response.text
        return response.json()['run_id']
    before = upload()
    assert choose(bob, [rel]).status_code == 200
    after = upload()
    import json
    def snapshot(rid):
        from pathlib import Path
        return json.loads(Path(ws.runs.get(rid)['json_path']).read_text())['terminology_snapshot']
    assert rel['id'] not in {r['id'] for r in snapshot(before)}
    assert rel['id'] in {r['id'] for r in snapshot(after)}
    assert choose(bob, [rel], False).status_code == 200
    restarted = Workspace(ws.path)
    try:
        assert TerminologyCatalog(restarted.repository).store(BOB).get(rel['id']) is None
        assert TerminologyCatalog(restarted.repository).store(ALICE).get(rel['id']) is not None
    finally:
        restarted.db.close()
    assert rel['id'] in {r['id'] for r in snapshot(after)}

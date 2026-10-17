"""Confidential pilot: enforce privacy at configuration and HTTP boundaries."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from kaizen.ai.providers import NullProvider, get_provider
from kaizen.api.app import create_app
from kaizen.review.access import AccessStore
from kaizen.review.auth import SupabaseAccounts
from kaizen.review.sessions import SessionStore
from kaizen.workspace import Workspace

EMAIL = 'private-pilot@bd.com'
PASSWORD = 'synthetic-private-pilot-password'


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv('KAIZEN_CONFIDENTIAL', '1')
    monkeypatch.setenv('KAIZEN_AI_PROVIDER', 'anthropic')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'synthetic-key-never-used')
    ws = Workspace(tmp_path / 'workspace')
    AccessStore(ws.db).bootstrap(EMAIL, PASSWORD)
    client = TestClient(create_app(ws))
    yield ws, client
    ws.db.close()


def test_confidential_mode_blocks_ai_even_when_configured(env, monkeypatch):
    from kaizen import ai
    def must_not_construct(*a, **k):
        raise AssertionError('An external provider must not even be constructed')
    monkeypatch.setattr(ai.providers, 'AnthropicProvider', must_not_construct)
    assert isinstance(get_provider(), NullProvider)
    assert get_provider().describe()['model'] is None


def test_explicit_external_provider_cannot_bypass_confidential_pipeline(env):
    from kaizen.pipeline import Ingested, run_checks
    from kaizen.terminology.store import RelationshipStore
    class ForbiddenProvider:
        def describe(self):
            raise AssertionError('External provider used')
        def adjudicate(self, *a, **k):
            raise AssertionError('External provider called')
    from pathlib import Path
    run = run_checks(Ingested(root=Path('.'), documents=[], warnings=[]), RelationshipStore.default(), provider=ForbiddenProvider())
    assert run.metadata.ai_provider['provider'] == 'null'


def test_hosted_mode_cannot_disable_privacy(env, monkeypatch):
    monkeypatch.setenv('KAIZEN_HOSTED', '1')
    monkeypatch.setenv('KAIZEN_CONFIDENTIAL', '0')
    assert isinstance(get_provider(), NullProvider)
    assert env[1].get('/api/health').json()['confidential'] is True


def test_confidential_mode_rejects_external_accounts(env):
    ws, _ = env
    with pytest.raises(ValueError, match='requires local accounts'):
        create_app(ws, accounts=SupabaseAccounts('https://example.supabase.co', 'sb_publishable_synthetic'))


def test_cookie_and_server_session_expire_after_eight_hours(env):
    ws, client = env
    response = client.post('/api/auth/signin', json={'email': EMAIL, 'password': PASSWORD})
    assert response.status_code == 200
    assert 'Max-Age=28800' in response.headers['set-cookie']
    token = client.cookies.get('kaizen_session')
    before = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
    ws.db.conn.execute('UPDATE sessions SET created_at=? WHERE token=?', (before, token))
    ws.db.conn.commit()
    assert client.get('/api/profiles').status_code == 200
    expired = (datetime.now(timezone.utc) - timedelta(hours=8, seconds=1)).isoformat()
    ws.db.conn.execute('UPDATE sessions SET created_at=? WHERE token=?', (expired, token))
    ws.db.conn.commit()
    assert client.get('/api/profiles').status_code == 401
    assert client.get('/api/sessions/current').json()['session'] is None
    assert ws.db.conn.execute('SELECT ended_at FROM sessions WHERE token=?', (token,)).fetchone()['ended_at']
    assert SessionStore(ws.db).resolve(token) is None


@pytest.mark.parametrize('path', ['/api/health', '/api/profiles', '/api/runs'])
def test_sensitive_responses_never_enter_browser_cache(env, path):
    response = env[1].get(path)
    assert response.status_code in (200, 401)
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert response.headers['x-frame-options'] == 'DENY'


def test_hosted_errors_do_not_log_confidential_exception_text(env, caplog):
    _, client = env
    secret = 'synthetic-source-contents-should-never-enter-cloud-logs'
    @client.app.get('/api/test-private-error')
    def fail():
        raise RuntimeError(secret)
    assert client.post('/api/auth/signin', json={'email': EMAIL, 'password': PASSWORD}).status_code == 200
    checked = TestClient(client.app, raise_server_exceptions=False, cookies=client.cookies)
    response = checked.get('/api/test-private-error', params={'source': secret})
    assert response.status_code == 500
    assert secret not in response.text
    application_logs = '\n'.join(record.getMessage() for record in caplog.records if record.name.startswith('kaizen'))
    assert secret not in application_logs and 'RuntimeError' in application_logs

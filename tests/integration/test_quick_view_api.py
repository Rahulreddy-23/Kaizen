"""Quick view inherits run access, live review status and read-only guarantees."""

import pymupdf
import pytest
from fastapi.testclient import TestClient

from kaizen.api.app import RunCache, create_app
from kaizen.ingest.hashing import sha256_file
from kaizen.review.access import AccessStore
from kaizen.review.sessions import UserStore
from kaizen.workspace import Workspace
from tests.unit.test_quick_view import fixture


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = tmp_path_factory.mktemp("quick-view")
    ws = Workspace(root / "ws")
    access = AccessStore(ws.db)
    access.bootstrap("owner@bd.com", "test-password-long")
    client = TestClient(create_app(ws))
    client.post("/api/auth/signin", json={"email": "owner@bd.com", "password": "test-password-long"})
    run = fixture()
    for doc in run.documents:
        path = root / f"{doc.id}.pdf"
        with pymupdf.open() as pdf:
            p = pdf.new_page()
            p.insert_text((20, 40), doc.items[0].description)
            pdf.save(path)
        doc.path = str(path)
        doc.sha256 = sha256_file(path)
        for item in doc.items:
            item.evidence.file = str(path)
            item.evidence.file_sha256 = doc.sha256
    RunCache(ws).put(run)
    ws.db.conn.execute("UPDATE runs SET owner=? WHERE run_id=?", ("owner@bd.com", run.metadata.run_id))
    ws.db.conn.commit()
    yield ws, client, run
    ws.db.close()


def test_endpoint_pages_evidence_and_filters(env):
    ws, client, run = env
    base = f"/api/runs/{run.metadata.run_id}/quick-view"
    response = client.get(base)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1 and data["counts"]["matched"] == 1
    assert len(data["documents"]) == 3 and all(d["pages"] == 1 for d in data["documents"])
    assert client.get(base, params={"sku": "not-in-run"}).status_code == 404
    assert client.get(base, params={"limit": 0}).status_code == 422
    assert client.get(base, params={"offset": -1}).status_code == 422
    assert client.get(base, params={"view": "unsupported"}).status_code == 422
    assert client.get(base, params={"search": "unrelated"}).json()["total"] == 0
    assert client.get(base, params={"view": "text"}).json()["rows"][0]["cells"]["BOM"]["items"][0]["raw_text"]
    assert "no-store" in response.headers["cache-control"]


def test_only_signed_in_users_with_run_access_can_read_quick_view(env):
    ws, owner, run = env
    base = f"/api/runs/{run.metadata.run_id}/quick-view"
    other = TestClient(create_app(ws))
    assert other.get(base).status_code == 401
    UserStore(ws.db).create("viewer@bd.com", "other-test-password")
    AccessStore(ws.db).register("viewer@bd.com")
    AccessStore(ws.db).update("viewer@bd.com", "owner@bd.com", "approved", False)
    assert other.post("/api/auth/signin", json={"email": "viewer@bd.com", "password": "other-test-password"}).status_code == 200
    assert other.get(base).status_code == 404
    AccessStore(ws.db).share(run.metadata.run_id, "viewer@bd.com", "view", "owner@bd.com")
    assert other.get(base).status_code == 200
    before = ws.db.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    assert other.get(base, params={"view": "text"}).status_code == 200
    assert ws.db.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == before
    assert other.post(f"/api/runs/{run.metadata.run_id}/bulk-accept", json={}).status_code == 403


def test_decision_changes_are_visible_without_reparsing(env):
    ws, client, run = env
    base = f"/api/runs/{run.metadata.run_id}"
    detail = client.get(f"{base}/results/pair0").json()
    saved = client.post(f"{base}/decisions", json={"row_id": "pair0", "decision": "NEEDS_MORE_INFORMATION", "expected_revision": detail["revision"]})
    assert saved.status_code == 200, saved.text
    row = client.get(f"{base}/quick-view").json()["rows"][0]
    assert row["status"] == "attention" and row["cells"]["LABEL"]["status"] == "attention"
    assert any(c["state"] == "REVIEWED" for c in row["checks"])

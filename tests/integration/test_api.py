"""API contract used by the reviewer UI. Runs against a temporary workspace; no network."""

import io

import openpyxl
import pytest
from fastapi.testclient import TestClient

from kaizen.api.app import create_app
from kaizen.datasets.build import build_golden
from kaizen.workspace import Workspace


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    root = tmp_path_factory.mktemp("api")
    golden = build_golden(root / "golden")
    ws = Workspace(root / "ws")
    client = TestClient(create_app(ws))
    r = client.post("/api/runs/from-path", json={"path": str(golden)})
    assert r.status_code == 200, r.text
    return client, golden, ws, r.json()["run_id"]


def test_health_and_run_listing(env):
    client, golden, ws, run_id = env
    assert client.get("/api/health").json()["status"] == "ok"
    runs = client.get("/api/runs").json()
    assert any(x["run_id"] == run_id for x in runs)
    summary = client.get(f"/api/runs/{run_id}").json()
    assert summary["skus"] == 10 and summary["documents"] == 38 and summary["rows"] > 1000
    assert summary["counts"]["EXACT"] > 0 and summary["needs_validation"] > 0 and summary["auto_cleared"] > 0
    assert any(c["status"] == "MISSING_BOM" for c in summary["coverage"])
    assert "ENGINE_RECOMMENDED" in summary["state_counts"]
    assert summary["capabilities"] and summary["terminology_version"]


def test_results_queue_ordering_and_filters(env):
    client, golden, ws, run_id = env
    queue = client.get(f"/api/runs/{run_id}/results", params={"needs_validation": "true"}).json()
    assert queue["total"] > 0
    assert queue["rows"][0]["engine"]["severity"] == "BLOCKER"
    sevs = [r["engine"]["severity"] or "" for r in queue["rows"]]
    order = {"BLOCKER": 0, "MAJOR": 1, "MINOR": 2, "INFO": 3, "": 4}
    assert all(order[a] <= order[b] for a, b in zip(sevs, sevs[1:]))
    only = client.get(f"/api/runs/{run_id}/results", params={"check": "PCO_BOM", "sku": "1395108QNS", "discrepancy": "PCO_CHANGE_NOT_APPLIED"}).json()
    assert only["total"] == 1 and only["rows"][0]["check"] == "PCO_BOM"
    cls = client.get(f"/api/runs/{run_id}/results", params={"classification": "MISMATCH", "check": "BOM_LABEL"}).json()
    assert cls["total"] >= 3 and all(r["engine"]["classification"] == "MISMATCH" for r in cls["rows"])


def test_row_detail_with_evidence_and_page_image(env):
    client, golden, ws, run_id = env
    row = client.get(f"/api/runs/{run_id}/results", params={"check": "BOM_LABEL", "sku": "1295108FNS", "classification": "MISMATCH"}).json()["rows"][0]
    detail = client.get(f"/api/runs/{run_id}/results/{row['row_id']}").json()
    assert detail["result"]["row_id"] == row["row_id"]
    a, b = detail["evidence"]["a"], detail["evidence"]["b"]
    assert a["doc_id"] and a["page"] == 2 and a["bbox"] and a["locator"] and a["raw_text"]
    assert b["doc_id"] and b["page"] == 1 and b["bbox"]
    assert detail["history"][0]["event"] == "engine"
    img = client.get(f"/api/runs/{run_id}/documents/{a['doc_id']}/pages/{a['page']}", params={"highlight": row["row_id"]})
    assert img.status_code == 200 and img.headers["content-type"] == "image/png" and len(img.content) > 5000
    items = client.get(f"/api/runs/{run_id}/documents/{b['doc_id']}/items").json()
    assert items["doc_type"] == "LABEL" and len(items["items"]) >= 30 and items["items"][0]["bbox"] and items["items"][0]["page"] == 1
    docs = client.get(f"/api/runs/{run_id}/documents").json()
    assert any(d["doc_type"] == "PCO" for d in docs)


def test_decisions_blind_mode_disagreement_and_finalize(env):
    client, golden, ws, run_id = env
    row = client.get(f"/api/runs/{run_id}/results", params={"check": "BOM_LABEL", "sku": "1295108FNS", "classification": "MISMATCH"}).json()["rows"][0]
    rid = row["row_id"]
    r = client.post(f"/api/runs/{run_id}/decisions", json={"row_id": rid, "slot": 1, "reviewer": "Dharma", "decision": "CONFIRM_DISCREPANCY", "comment": "qty"})
    assert r.status_code == 200 and r.json()["state"] == "REVIEWER_1_COMPLETE"
    blind = client.get(f"/api/runs/{run_id}/results/{rid}", params={"viewer": 2, "blind": "true"}).json()
    assert blind["decisions"]["1"] is None and blind["result"]["classification"] == "MISMATCH"
    r = client.post(f"/api/runs/{run_id}/decisions", json={"row_id": rid, "slot": 2, "reviewer": "Hemant", "decision": "ACCEPT", "blind": True})
    assert r.json()["state"] == "DISAGREEMENT"
    after = client.get(f"/api/runs/{run_id}/results/{rid}", params={"viewer": 2, "blind": "true"}).json()
    assert after["decisions"]["1"]["decision"] == "CONFIRM_DISCREPANCY"
    r = client.post(f"/api/runs/{run_id}/finalize", json={"row_id": rid, "final_decision": "CONFIRM_DISCREPANCY", "by": "Dharma", "note": "meeting"})
    assert r.json()["state"] == "FINALIZED"
    bad = client.post(f"/api/runs/{run_id}/decisions", json={"row_id": rid, "slot": 1, "reviewer": "x", "decision": "MAYBE"})
    assert bad.status_code == 400
    n = client.post(f"/api/runs/{run_id}/bulk-accept", json={"slot": 1, "reviewer": "Dharma"}).json()["accepted"]
    assert n > 100


def test_save_as_relationship_and_next_run_uses_it(env):
    client, golden, ws, run_id = env
    row = client.get(f"/api/runs/{run_id}/results", params={"check": "BOM_LABEL", "sku": "1295108NS", "classification": "POTENTIAL"}).json()["rows"]
    chlora = next(r for r in row if "CHLORAPREP" in r["engine"]["explanation"].upper())
    r = client.post(f"/api/runs/{run_id}/relationships/from-row", json={"row_id": chlora["row_id"], "by": "Dharma", "scope": "global", "anchor": True, "notes": "confirmed in review"})
    assert r.status_code == 200, r.text
    rel = r.json()
    assert rel["provenance"] == "learned" and rel["item_anchors"] == ["4440003"] and rel["created_by"] == "Dharma"
    assert "CHLORAPREP APPLICATOR 3ML" in rel["aliases"]
    r2 = client.post("/api/runs/from-path", json={"path": str(golden / "sku-002")})
    run2 = r2.json()["run_id"]
    rows = client.get(f"/api/runs/{run2}/results", params={"check": "BOM_LABEL", "sku": "1295108FNS"}).json()["rows"]
    again = next(x for x in rows if "CHLORAPREP" in x["engine"]["explanation"].upper())
    assert again["engine"]["classification"] == "EQUIVALENT" and again["engine"]["relationship_id"] == rel["id"]


def test_mining_action_items_verify_close_business_and_exports(env):
    client, golden, ws, run_id = env
    sugg = client.get(f"/api/runs/{run_id}/mining").json()
    assert sugg and sugg[0]["sku_count"] >= 2 and sugg[0]["evidence"]
    s = next(x for x in sugg if "LIDOCAINE" in x["a_text"].upper())
    r = client.post(f"/api/runs/{run_id}/mining/approve", json={"a_key": s["a_key"], "b_key": s["b_key"], "by": "Hemant", "scope": "global"})
    assert r.status_code == 200 and r.json()["id"].startswith("REL-")
    s2 = next(x for x in sugg if "GUIDEWIRE" in x["a_text"].upper())
    assert client.post(f"/api/runs/{run_id}/mining/reject", json={"a_key": s2["a_key"], "b_key": s2["b_key"], "by": "Hemant", "note": "different"}).status_code == 200
    assert not any(x["a_key"] == s2["a_key"] for x in client.get(f"/api/runs/{run_id}/mining").json())

    row = client.get(f"/api/runs/{run_id}/results", params={"check": "PCO_BOM", "sku": "1395108QNS", "discrepancy": "PCO_CHANGE_NOT_APPLIED"}).json()["rows"][0]
    ai = client.post(f"/api/runs/{run_id}/action-items", json={"row_id": row["row_id"], "reviewer": "Dharma", "owner": "R&D"}).json()
    assert ai["id"].startswith("AI-") and ai["status"] == "OPEN"
    assert client.patch(f"/api/action-items/{ai['id']}", json={"status": "IN_PROGRESS", "by": "Hemant"}).json()["status"] == "IN_PROGRESS"
    assert any(x["id"] == ai["id"] for x in client.get("/api/action-items").json())
    r3 = client.post("/api/runs/from-path", json={"path": str(golden / "sku-002")}).json()["run_id"]
    vc = client.post(f"/api/runs/{r3}/verify-and-close").json()
    assert ai["id"] in vc["not_covered"]

    bc = client.get(f"/api/runs/{run_id}/business-case").json()
    assert bc["skus"] == 10 and "annual_savings" in bc and bc["assumptions"]
    bc2 = client.get(f"/api/runs/{run_id}/business-case", params={"minutes_per_validation_row": 5}).json()
    assert bc2["estimated_minutes_per_sku"] > bc["estimated_minutes_per_sku"]

    x = client.get(f"/api/runs/{run_id}/export.xlsx")
    assert x.status_code == 200 and "spreadsheet" in x.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert "Action_Items" in wb.sheetnames
    docs = client.get(f"/api/runs/{run_id}/documents").json()
    bom = next(d for d in docs if d["doc_type"] == "BOM" and d["sku"] == "1295108FNS")
    pdf = client.get(f"/api/runs/{run_id}/annotated-bom/{bom['id']}")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"


def test_terminology_endpoints(env):
    client, golden, ws, run_id = env
    rels = client.get("/api/terminology").json()
    assert any(r["id"] == "REL-001" and "usage" in r for r in rels)
    r = client.post("/api/terminology", json={"canonical": "Vessel Dilator", "aliases": ["DILATOR VESSEL"], "scope": "global", "by": "rahul", "notes": "api"})
    rid = r.json()["id"]
    assert client.put(f"/api/terminology/{rid}", json={"aliases": ["DILATOR VESSEL", "VESSEL DILATOR"], "by": "rahul", "note": "alias"}).json()["version"] == 2
    assert len(client.get(f"/api/terminology/{rid}/history").json()) == 2
    assert client.post(f"/api/terminology/{rid}/deactivate", json={"by": "rahul"}).json()["active"] is False
    assert client.get("/api/terminology", params={"search": "vessel", "all": "true"}).json()
    x = client.get("/api/terminology/export.xlsx")
    assert x.status_code == 200
    up = client.post("/api/terminology/import", files={"file": ("rels.xlsx", x.content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, data={"by": "rahul"})
    assert up.status_code == 200 and "unchanged" in up.json()["summary"]


def test_upload_and_demo(env):
    client, golden, ws, run_id = env
    files = []
    for p in sorted((golden / "sku-001").iterdir()):
        files.append(("files", (f"sku-001/{p.name}", p.read_bytes(), "application/octet-stream")))
    r = client.post("/api/runs/upload", files=files)
    assert r.status_code == 200, r.text
    assert r.json()["skus"] == 1
    d = client.post("/api/demo/load")
    assert d.status_code == 200 and d.json()["skus"] >= 8

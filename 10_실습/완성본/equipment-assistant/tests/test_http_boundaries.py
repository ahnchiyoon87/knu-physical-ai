"""HTTP input and role checks only; persistence and model paths are not exercised."""
from fastapi.testclient import TestClient
from backend.api import app


def test_anonymous_request_cannot_create_a_proposal(monkeypatch):
    monkeypatch.setenv("SERVICE_TOKEN","test-service")
    client=TestClient(app)
    response=client.post("/api/process/propose",json={"rule_id":"r","event_ids":["e"],"new_width":2,"rationale":"check"})
    assert response.status_code==401 and response.json()["status"]=="error"


def test_service_access_is_not_human_approval(monkeypatch):
    monkeypatch.setenv("SERVICE_TOKEN","test-service")
    monkeypatch.setenv("APPROVER_TOKEN","test-approver")
    client=TestClient(app)
    response=client.post("/api/approvals/p/decide",headers={"Authorization":"Bearer test-service"},
                         json={"version":1,"payload_hash":"hash","approved":True,"actor":"reviewer","reason":"checked"})
    assert response.status_code==403 and response.json()["status"]=="error"


def test_malformed_request_never_reaches_database(monkeypatch):
    monkeypatch.setenv("SERVICE_TOKEN","test-service")
    client=TestClient(app)
    response=client.post("/api/data/series",headers={"Authorization":"Bearer test-service"},
                         json={"profile":"synthetic","source_id":"shots","column_id":"unknown"})
    assert response.status_code==422 and response.json()["status"]=="error"

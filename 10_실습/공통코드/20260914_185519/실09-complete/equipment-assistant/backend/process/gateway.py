"""Approval and rule changes share a transaction; graph changes use an outbox."""
from uuid import uuid4

from psycopg.types.json import Jsonb

from backend.common.gateway import database
from backend.common.log import span
from backend.common.service import fingerprint


def create_proposal(payload: dict) -> dict:
    identity = str(uuid4())
    digest = fingerprint(payload)
    with span("process", "process.propose", "backend/process/gateway.py:create_proposal"), database() as db:
        db.execute("INSERT INTO lab.proposals(id,status,payload,payload_hash) VALUES(%s,'pending_approval',%s,%s)",
                   (identity, Jsonb(payload), digest))
    return {"id": identity, "version": 1, "payload_hash": digest, "status": "pending_approval", "payload": payload}


def proposal(identity: str) -> dict | None:
    with database(readonly=True) as db:
        return db.execute("SELECT * FROM lab.proposals WHERE id=%s", (identity,)).fetchone()


def proposals() -> list[dict]:
    with database(readonly=True) as db:
        return db.execute("SELECT * FROM lab.proposals ORDER BY created_at DESC LIMIT 100").fetchall()


def decide(identity: str, version: int, payload_hash: str, approved: bool, actor: str, reason: str):
    with span("process", "process.approval", "backend/process/gateway.py:decide"), database() as db:
        row = db.execute("SELECT * FROM lab.proposals WHERE id=%s FOR UPDATE", (identity,)).fetchone()
        if row is None:
            raise ValueError("승인 대상이 없습니다")
        if row["version"] != version or row["payload_hash"] != payload_hash:
            raise ValueError("승인 대상의 내용 또는 버전이 다릅니다")
        requested_status = "approved" if approved else "rejected"
        if row["status"] != "pending_approval":
            if row["status"] == requested_status and row["actor"] == actor and row["reason"] == reason:
                return {"id": identity, "status": row["status"], "duplicate": True}
            raise ValueError("이미 결정된 제안입니다. 기존 결정을 바꾸지 않았습니다")
        db.execute("UPDATE lab.proposals SET status=%s,actor=%s,reason=%s,decided_at=now() WHERE id=%s",
                   (requested_status, actor, reason, identity))
        return {"id": identity, "status": requested_status, "duplicate": False}


def record(identity: str, version: int, payload_hash: str):
    with span("process", "process.record", "backend/process/gateway.py:record"), database() as db:
        row = db.execute("SELECT * FROM lab.proposals WHERE id=%s FOR UPDATE", (identity,)).fetchone()
        if not row or row["version"] != version or row["payload_hash"] != payload_hash:
            raise ValueError("제안의 대상·버전·내용을 확인하세요")
        previous = db.execute("SELECT * FROM lab.decisions WHERE proposal_id=%s", (identity,)).fetchone()
        if previous:
            if row["status"] != "recorded":
                raise ValueError("결정 기록과 제안 상태가 일치하지 않습니다")
            return {"id": identity, "duplicate": True, "decision": previous}
        if row["status"] != "approved":
            raise ValueError("승인된 제안만 기록할 수 있습니다")
        payload = row["payload"]
        if fingerprint(payload) != payload_hash:
            raise ValueError("저장된 제안 내용이 변경됐습니다")
        before = db.execute("SELECT id,version,definition FROM lab.rules WHERE id=%s FOR UPDATE", (payload["rule_id"],)).fetchone()
        if before is None or before["version"] != payload["expected_rule_version"]:
            raise ValueError("승인 후 규칙 버전이 달라졌습니다. 현재 규칙으로 새 제안을 만드세요")
        after = {**before["definition"], "width": payload["new_width"]}
        db.execute("UPDATE lab.rules SET definition=%s,version=version+1,updated_at=now() WHERE id=%s",
                   (Jsonb(after), before["id"]))
        db.execute("INSERT INTO lab.decisions(proposal_id,proposal_version,payload_hash,actor,reason,"
                   "before_rule,after_rule) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                   (identity, version, payload_hash, row["actor"], row["reason"],
                    Jsonb(before), Jsonb({"id": before["id"], "version": before["version"] + 1, "definition": after})))
        db.execute("UPDATE lab.proposals SET status='recorded' WHERE id=%s", (identity,))
        graph = {"id": identity, "kind": "decision", "status": "recorded", "provenance": "설계: 승인된 서비스 기록",
                 "targets": payload["event_ids"] + [payload["rule_id"]]}
        db.execute("INSERT INTO lab.graph_outbox(id,payload) VALUES(%s,%s) ON CONFLICT(id) DO NOTHING",
                   (identity, Jsonb(graph)))
        decision = db.execute("SELECT * FROM lab.decisions WHERE proposal_id=%s", (identity,)).fetchone()
        if decision["payload_hash"] != payload_hash:
            raise ValueError("결정 기록을 되읽은 결과가 다릅니다")
        return {"id": identity, "duplicate": False, "decision": decision, "graph_status": "queued"}


def guard_inputs(rule_id: str, event_ids: list[str]):
    with database(readonly=True) as db:
        rule = db.execute("SELECT id,version,definition FROM lab.rules WHERE id=%s AND active", (rule_id,)).fetchone()
        events = db.execute("SELECT id,profile,source_id,method FROM lab.events WHERE id=ANY(%s)", (event_ids,)).fetchall()
    return rule, events

"""Evaluation artifacts use the same database and request-scoped model accounting."""
from psycopg.types.json import Jsonb

from backend.common.gateway import database
from backend.common.log import span


def save(identity: str, rid: str, provider: str, payload: dict):
    with span("eval", "eval.run", "backend/eval/gateway.py:save", cases=len(payload["results"])), database() as db:
        db.execute("INSERT INTO lab.evaluations(id,request_id,provider,payload) VALUES(%s,%s,%s,%s)",
                   (identity, rid, provider, Jsonb(payload)))


def load(identity: str):
    with database(readonly=True) as db:
        row = db.execute("SELECT payload FROM lab.evaluations WHERE id=%s", (identity,)).fetchone()
    if row is None:
        raise ValueError("평가 기록이 없습니다")
    return row["payload"]

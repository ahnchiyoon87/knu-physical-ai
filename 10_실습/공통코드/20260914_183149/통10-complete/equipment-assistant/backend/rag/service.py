"""Only current, scoped evidence may support an answer."""
from backend.common.config import mapping
from backend.common.response import reply

from . import gateway


def documents(profile: str) -> list[dict]:
    config = mapping()["profiles"].get(profile)
    if not config:
        raise ValueError("등록되지 않은 자료 프로필입니다")
    return config.get("documents", [])


def index(rid: str, profile: str):
    return reply(rid, gateway.index_documents(documents(profile)))


def search(rid: str, profile: str, question: str):
    rows = gateway.search(question, [document["id"] for document in documents(profile)])
    evidence = [{"kind": "doc", "ref": f"[{row['document_id']} §{row['section']}] {row['title']}",
                 "quote": row["body"], "status": row["status"], "chunk_id": row["id"],
                 "document_id": row["document_id"], "provenance": row["provenance"]} for row in rows]
    return reply(rid, [{"rank": index + 1, "score": row["score"]} for index, row in enumerate(rows)],
                 evidence=evidence, status="ok" if rows else "none",
                 reason="" if rows else "조건을 만족하는 현행 근거가 없습니다")


def ask(rid: str, profile: str, question: str, provider: str, context: dict | None = None):
    retrieved = search(rid, profile, question)
    if retrieved.status != "ok":
        return reply(rid, status="refused", reason=retrieved.reason)
    numbered = [{"id": index, **item} for index, item in enumerate(retrieved.evidence)]
    draft, meta = gateway.answer(provider, question, numbered, context)
    if draft.get("sufficient") is not True or not draft.get("claims"):
        return reply(rid, status="refused", reason=draft.get("reason") or "근거가 부족합니다", evidence=retrieved.evidence, meta=meta)
    for claim in draft["claims"]:
        ids = claim.get("evidence_ids")
        if not ids or any(type(index) is not int or not 0 <= index < len(numbered) for index in ids):
            return reply(rid, status="failed", reason="등록되지 않은 인용 번호가 있습니다", meta=meta)
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            return reply(rid, status="failed", reason="주장 본문이 비어 있습니다", meta=meta)
    meta["warnings"].append("인용 번호의 존재를 확인했습니다. 문장이 근거로 지지되는지는 별도 평가 대상입니다")
    return reply(rid, draft["claims"], evidence=numbered, meta=meta)

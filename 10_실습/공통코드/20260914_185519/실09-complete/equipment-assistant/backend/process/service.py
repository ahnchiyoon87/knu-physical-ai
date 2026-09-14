"""Guard action scope before proposing; approval never comes from the language model."""
from backend.common.config import settings
from backend.common.response import reply
from backend.common.service import finite_number

from . import gateway


def propose(rid: str, rule_id: str, event_ids: list[str], new_width: float, rationale: str):
    width = finite_number(new_width, "새 규칙 폭")
    low, high = settings()["agent"]["allowed_rule_width"]
    if not low <= width <= high:
        return reply(rid, status="refused", reason="서비스 계약의 규칙 폭 허용 범위를 벗어났습니다")
    if not event_ids or len(event_ids) != len(set(event_ids)) or not rationale.strip():
        raise ValueError("중복 없는 이벤트 근거와 제안 이유가 필요합니다")
    rule, events = gateway.guard_inputs(rule_id, event_ids)
    if rule is None or len(events) != len(event_ids):
        return reply(rid, status="insufficient", reason="현재 규칙 또는 이벤트 근거가 없습니다")
    if rule["definition"]["mode"] not in {"relative", "combined"}:
        return reply(rid, status="refused", reason="폭 변경은 상대 또는 조합 규칙에서만 의미가 있습니다")
    if any(event["profile"] != rule["definition"]["profile"] or
           event["source_id"] != rule["definition"]["source_id"] for event in events):
        raise ValueError("이벤트와 규칙의 원천이 다릅니다")
    if any(event["method"] != f"rule:{rule_id}:{rule['version']}" for event in events):
        return reply(rid, status="insufficient", reason="현재 규칙 버전으로 재생한 이벤트 근거가 필요합니다")
    payload = {"rule_id": rule_id, "expected_rule_version": rule["version"],
               "event_ids": event_ids, "new_width": width, "rationale": rationale,
               "profile": rule["definition"]["profile"], "source_id": rule["definition"]["source_id"],
               "action_scope": "기록된 데이터를 재생하는 소프트웨어 규칙. 실제 설비 제어 아님"}
    result = gateway.create_proposal(payload)
    return reply(rid, result, status="pending_approval", reason="사람의 승인 또는 반려를 기다립니다")


def decide(rid: str, identity: str, version: int, payload_hash: str, approved: bool, actor: str, reason: str):
    if not actor.strip() or not reason.strip():
        raise ValueError("판단자 역할과 사유가 필요합니다")
    return reply(rid, gateway.decide(identity, version, payload_hash, approved, actor, reason))


def record(rid: str, identity: str, version: int, payload_hash: str):
    return reply(rid, gateway.record(identity, version, payload_hash))

"""Rules and model outputs remain observations rather than confirmed diagnoses."""
from backend.common.config import source
from backend.common.response import reply

from . import gateway
from .rules import detect_rows


def run_rules(rid: str, profile: str, source_id: str, rule_id: str):
    selected = gateway.rule(rule_id)
    if selected is None:
        return reply(rid, status="none", reason="활성 규칙이 없습니다")
    definition = {**selected["definition"], "version": selected["version"]}
    if definition["profile"] != profile or definition["source_id"] != source_id:
        raise ValueError("규칙의 원천과 요청 원천이 다릅니다")
    try:
        rows = gateway.rule_rows(profile, source_id, definition)
    except ValueError as exc:
        return reply(rid,status="insufficient",reason=str(exc))
    if not rows:
        return reply(rid, status="insufficient", reason="적재된 감지 입력이 없습니다")
    try:
        alarms = detect_rows(rows, definition)
    except ValueError as exc:
        return reply(rid,status="insufficient",reason=str(exc))
    provenance = source(source_id, profile)["provenance"]
    gateway.save_events(profile, source_id, f"rule:{rule_id}:{selected['version']}", alarms, provenance)
    answer = {"evaluated": len(rows), "flagged": len(alarms),
              "notified": sum(not x["suppressed"] for x in alarms),
              "suppressed": sum(x["suppressed"] for x in alarms), "rule_version": selected["version"],
              "preview": alarms[:20], "provenance": provenance,
              "graph_status": "queued", "label_evaluation": "미수행: 정답 라벨과 대조하지 않았습니다"}
    return reply(rid, answer, evidence=[{"kind": "table", "ref": source_id, "rows": len(rows)}])


def list_events(rid: str, profile: str, source_id: str, lot_id: str | None = None):
    source(source_id, profile)
    rows = gateway.events(profile, source_id, lot_id)
    return reply(rid, {"rows": rows[:500], "truncated": len(rows) > 500},
                 status="ok" if rows else "none", reason="" if rows else "관련 이벤트가 없습니다")

"""Graph paths are relationship evidence, not causal proof."""
from backend.common.config import mapping
from backend.common.response import reply

from . import gateway


def load(rid: str, profile: str):
    config = mapping()["profiles"].get(profile)
    if config is None:
        raise ValueError("알 수 없는 프로필입니다")
    return reply(rid, gateway.load_relationships(config["ontology"]))


def path(rid: str, start: str, end: str):
    if not start.strip() or not end.strip():
        raise ValueError("시작과 끝 대상을 지정하세요")
    rows = gateway.paths(start, end)
    evidence = [{"kind": "path", "ref": " → ".join(n["id"] for n in row["nodes"]),
                 "hops": len(row["relations"]), "relations": row["relations"]} for row in rows]
    return reply(rid, rows, status="ok" if rows else "none", evidence=evidence,
                 reason="" if rows else "설정한 탐색 범위 안에서 관계를 찾지 못했습니다",
                 meta={"warnings": ["관련 경로는 실제 고장의 인과를 증명하지 않습니다"]})

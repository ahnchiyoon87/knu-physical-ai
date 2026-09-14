"""Read persisted model relationships for the early relationship-table view."""
from backend.common.gateway import database


def related_rows(start, end):
    # Fail visibly if a broad target exceeds the inspection limit; do not silently truncate.
    with database() as db:
        records = db.execute(
            "SELECT payload FROM lab.graph_outbox WHERE payload->>'kind'='model_result' AND "
            "(payload->>'id' IN (%s,%s) OR EXISTS (SELECT 1 FROM jsonb_array_elements("
            "COALESCE(payload->'edges','[]'::jsonb)) edge WHERE edge->>'source' IN (%s,%s) "
            "OR edge->>'target' IN (%s,%s))) ORDER BY created_at LIMIT 201",
            (start,end,start,end,start,end)).fetchall()
    if len(records) > 200:
        raise ValueError("관련 분석 기록이 200개를 넘습니다. 결과 ID와 원본 행 ID로 범위를 좁히세요")
    return [edge for record in records for edge in record["payload"].get("edges", [])]

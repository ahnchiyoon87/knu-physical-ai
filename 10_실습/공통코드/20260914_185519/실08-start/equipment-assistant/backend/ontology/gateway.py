"""Neo4j relationship projection with transactional read-back."""
import csv

from neo4j import GraphDatabase

from backend.common.config import configured_path, env, settings
from backend.common.gateway import database
from backend.common.log import span


def driver():
    return GraphDatabase.driver(env("NEO4J_URI"), auth=(env("NEO4J_USER"), env("NEO4J_PASSWORD")))


def load_relationships(path: str):
    with configured_path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or set(rows[0]) != {"source", "source_type", "relation", "target", "target_type", "provenance"}:
        raise ValueError("온톨로지 표의 열과 내용을 확인하세요")
    if any(not all(row.values()) for row in rows):
        raise ValueError("온톨로지의 빈 항목을 먼저 채우세요")
    with span("ontology", "ontology.load", "backend/ontology/gateway.py:load_relationships", rows=len(rows)), driver() as graph, graph.session() as session:
        session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE").consume()
        def write(tx):
            for row in rows:
                tx.run("MERGE(a:Entity {id:$source}) SET a.kind=$source_type "
                       "MERGE(b:Entity {id:$target}) SET b.kind=$target_type "
                       "MERGE(a)-[r:REL {kind:$relation}]->(b) SET r.provenance=$provenance", **row).consume()
            matched = tx.run("UNWIND $rows AS row MATCH(a:Entity {id:row.source})"
                             "-[r:REL {kind:row.relation}]->(b:Entity {id:row.target}) "
                             "RETURN count(*) AS count", rows=rows).single()["count"]
            if matched != len(rows):
                raise ValueError("그래프 적재와 되읽기 개수가 다릅니다")
            return {"relationships": matched}
        return session.execute_write(write)


def paths(start: str, end: str) -> list[dict]:
    hops = int(settings()["agent"]["max_graph_hops"])
    if not 1 <= hops <= 8:
        raise ValueError("그래프 탐색 상한은 1~8입니다")
    statement = ("MATCH(a:Entity {id:$start}),(b:Entity {id:$end}), "
                 f"p=shortestPath((a)-[:REL*1..{hops}]-(b)) "
                 "RETURN [n IN nodes(p)|{id:n.id,kind:n.kind}] AS nodes, "
                 "[r IN relationships(p)|{kind:r.kind,provenance:r.provenance}] AS relations LIMIT 10")
    with span("ontology", "ontology.path", "backend/ontology/gateway.py:paths"), driver() as graph, graph.session() as session:
        return [record.data() for record in session.run(statement, start=start, end=end)]


def flush_outbox() -> dict:
    applied = 0
    # Holding the row lock across the graph write prevents concurrent workers from duplicating work.
    # The graph MERGE is still necessary after a database commit failure.
    with database() as db:
        pending = db.execute("SELECT id,payload FROM lab.graph_outbox WHERE applied_at IS NULL "
                             "ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 100").fetchall()
        with driver() as graph, graph.session() as session:
            for row in pending:
                payload = row["payload"]
                def write(tx, payload=payload):
                    tx.run("MERGE(n:Entity {id:$id}) SET n.kind=$kind, n.status=$status",
                           id=payload["id"], kind=payload["kind"], status=payload["status"]).consume()
                    for target in payload.get("targets", []):
                        tx.run("MATCH(n:Entity {id:$id}) MERGE(t:Entity {id:$target}) "
                               "MERGE(n)-[r:REL {kind:'related_to'}]->(t) SET r.provenance=$provenance",
                               id=payload["id"], target=target, provenance=payload["provenance"]).consume()
                    for edge in payload.get("edges", []):
                        tx.run("MERGE(a:Entity {id:$source}) SET a.kind=$source_type "
                               "MERGE(b:Entity {id:$target}) SET b.kind=$target_type "
                               "MERGE(a)-[r:REL {kind:$relation}]->(b) SET r.provenance=$provenance",
                               **edge).consume()
                        found = tx.run("MATCH(a:Entity {id:$source})-[r:REL {kind:$relation}]->"
                                       "(b:Entity {id:$target}) RETURN r.provenance AS provenance",
                                       **edge).single()
                        if not found or found["provenance"] != edge["provenance"]:
                            raise ValueError("분류 행 관계를 되읽은 결과가 다릅니다")
                    return tx.run("MATCH(n:Entity {id:$id}) RETURN n.status AS status",
                                  id=payload["id"]).single()["status"]
                observed = session.execute_write(write)
                if observed != payload["status"]:
                    raise ValueError("그래프 상태를 되읽은 결과가 다릅니다")
                db.execute("UPDATE lab.graph_outbox SET applied_at=now(),error_type=NULL WHERE id=%s", (row["id"],))
                applied += 1
        remaining = db.execute("SELECT count(*) AS n FROM lab.graph_outbox WHERE applied_at IS NULL").fetchone()["n"]
    return {"applied": applied, "remaining": remaining,
            "status": "pending" if remaining else "synchronized",
            "next": "남은 건수가 있으면 명시적으로 다시 동기화하세요" if remaining else ""}

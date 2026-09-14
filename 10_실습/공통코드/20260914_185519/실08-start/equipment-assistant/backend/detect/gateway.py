"""Detection persistence and explicitly requested CPU model loading."""
from psycopg import sql
from psycopg.types.json import Jsonb

from backend.common.config import source,analysis_source
from backend.common.gateway import database
from backend.common.log import span
from backend.common.service import fingerprint


def all_series(profile: str, source_id: str, column_id: int, lot_id: str | None = None) -> list[dict]:
    config = analysis_source(source_id, profile)
    column = next((c for c in config["columns"] if c["id"] == column_id), None)
    if not column or column["type"] != "number":
        raise ValueError("수치 열 번호를 선택하세요")
    query = sql.SQL("SELECT row_no,lot_id,{} AS value FROM lab.{}").format(
        sql.Identifier(f"c{column_id}"), sql.Identifier(config["table"]))
    params = ()
    if lot_id is not None:
        query += sql.SQL(" WHERE lot_id=%s")
        params = (lot_id,)
    query += sql.SQL(" ORDER BY row_no")
    with span("detect", "detect.rule", "backend/detect/gateway.py:all_series", source=source_id), database(readonly=True) as db:
        return db.execute(query, params).fetchall()


def rule(rule_id: str):
    with database(readonly=True) as db:
        return db.execute("SELECT id,version,definition FROM lab.rules WHERE id=%s AND active", (rule_id,)).fetchone()


def rule_rows(profile,source_id,definition):
    rows=all_series(profile,source_id,definition['column_id'])
    if definition['mode']=='multichannel':
        columns={c['column_id'] for c in definition['conditions']}
        index={(row['lot_id'],row['row_no']):row for row in rows}
        for row in rows:row['channels']={}
        for cid in columns:
            values=all_series(profile,source_id,cid)
            if {(row['lot_id'],row['row_no']) for row in values}!=set(index):
                raise ValueError('조합 채널의 관측 키가 일치하지 않습니다')
            for row in values:index[(row['lot_id'],row['row_no'])]['channels'][str(cid)]=row['value']
    reference=definition.get('condition_reference')
    if reference:
        config=source(reference['source_id'],profile)
        column=next((c for c in config['columns'] if c['id']==reference['column_id']),None)
        if not column or column['type']!='number':raise ValueError('조건표 수치 열을 확인하세요')
        with database(readonly=True) as db:
            conditions=db.execute(sql.SQL('SELECT lot_id,{} AS reference FROM lab.{}').format(
                sql.Identifier('c'+str(column['id'])),sql.Identifier(config['table']))).fetchall()
        by_lot={}
        for condition in conditions:
            if condition['lot_id'] in by_lot:raise ValueError('LOT에 적용할 조건표 행이 여러 개입니다. 개정을 먼저 선택하세요')
            by_lot[condition['lot_id']]=condition['reference']
        from backend.common.service import finite_number
        width=finite_number(reference['width'],'허용 폭')
        if width<=0:raise ValueError('허용 폭은 양수여야 합니다')
        for row in rows:
            value=by_lot.get(row['lot_id'])
            if value is None:raise ValueError('LOT '+str(row['lot_id'])+'의 적용 조건이 없습니다')
            value=finite_number(value,'조건표 기준')
            row.update(lower=value-width,upper=value+width,condition_source=reference['source_id'],
                       condition_reference=value,condition_provenance=config['provenance'])
    return rows


def save_events(profile: str, source_id: str, method: str, records: list[dict], provenance: str):
    with span("detect", "detect.event", "backend/detect/gateway.py:save_events", count=len(records)), database() as db:
        for row in records:
            identity = fingerprint([profile, source_id, method, row])
            db.execute("INSERT INTO lab.events(id,profile,source_id,lot_id,row_no,kind,method,payload) "
                       "VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING",
                       (identity, profile, source_id, row.get("lot_id"), row.get("row_no"),
                        "alarm", method, Jsonb({**row, "provenance": provenance})))
            projection = {"id": identity, "kind": "alarm", "status": "observed", "provenance": provenance,
                          "targets": [f"{profile}:{source_id}:lot:{row['lot_id']}"] if row.get("lot_id") else []}
            db.execute("INSERT INTO lab.graph_outbox(id,payload) VALUES(%s,%s) ON CONFLICT(id) DO NOTHING",
                       (identity, Jsonb(projection)))


def events(profile: str, source_id: str, lot_id: str | None = None):
    with database(readonly=True) as db:
        available=db.execute("SELECT to_regclass('lab.proposals') IS NOT NULL AND to_regclass('lab.decisions') IS NOT NULL AS present").fetchone()['present']
        status=("CASE WHEN EXISTS (SELECT 1 FROM lab.proposals p JOIN lab.decisions d ON d.proposal_id=p.id "
                "WHERE p.status='recorded' AND p.payload->'event_ids' ? e.id) THEN 'recorded' ELSE 'observed' END"
                if available else "'observed'")
        return db.execute("SELECT e.id,e.lot_id,e.row_no,e.kind,e.method,e.payload, "
                          +status+" AS action_status FROM lab.events e "
                          "WHERE e.profile=%s AND e.source_id=%s AND (%s::text IS NULL OR e.lot_id=%s) "
                          "ORDER BY e.row_no LIMIT 501", (profile, source_id, lot_id, lot_id)).fetchall()


"""Catalog meaning, scoped SQL answers, quality measurements and series."""
from backend.common.config import mapping, source, analysis_source
from backend.common.response import reply
from backend.common.service import combine_metrics
from . import gateway

def catalog(profile: str) -> list[dict]:
    if profile not in mapping()['profiles']:
        raise ValueError('등록되지 않은 자료 프로필입니다')
    return [{'source_id': key, 'table': value['table'], 'provenance': value['provenance'], 'time_column': value.get('time_column'), 'lot_rule': value.get('lot_rule'), 'joins': value.get('joins', []), 'columns': value['columns']} for key in mapping()['profiles'][profile]['sources'] for value in [analysis_source(key, profile)]]

def upload(rid: str, profile: str, source_id: str):
    config = source(source_id, profile)
    return reply(rid, gateway.import_csv(profile, source_id, config))

def question(rid: str, profile: str, source_ids: list[str], text: str, provider: str, context: dict | None=None, verify: bool=True, context_level: str='probed'):
    if not text.strip() or not source_ids:
        raise ValueError('질문과 원천을 선택하세요')
    if context and (context.get('profile') != profile or set(context.get('source_ids', [])) != set(source_ids)):
        raise ValueError('이전 대화의 자료와 현재 선택이 다릅니다. 새 질문으로 시작하세요')
    selected = [entry for entry in catalog(profile) if entry['source_id'] in source_ids]
    if len(selected) != len(set(source_ids)):
        raise ValueError('선택한 원천이 프로필에 없습니다')
    if context_level not in {'names', 'dictionary', 'probed'}:
        raise ValueError('질문에 전달할 정보 수준을 확인하세요')
    probes = gateway.probe_sources(selected) if context_level == 'probed' else []
    catalog_input = selected
    if context_level == 'names':
        catalog_input = [{'source_id': entry['source_id'], 'table': entry['table'], 'columns': [{k: c[k] for k in ('id', 'name', 'type')} for c in entry['columns']]} for entry in selected]
    proposal, meta = gateway.sql_from_question(provider, text, catalog_input, context, probes)
    calls = [meta]
    if proposal.get('sufficient') is not True:
        return reply(rid, status='insufficient', reason=proposal.get('reason') or '질문 조건 부족', meta=meta)
    allowed_ids = {column['id'] for entry in selected for column in entry['columns']}
    ids = proposal.get('column_ids')
    if not isinstance(ids, list) or any((type(number) is not int or number not in allowed_ids for number in ids)):
        return reply(rid, status='failed', reason='모델이 등록되지 않은 열 번호를 선택했습니다', meta=meta)
    result = gateway.query_rows(proposal['sql'], {entry['table'] for entry in selected})
    history = []
    semantic = []
    if verify and result['rows']:
        judged, judge_meta = gateway.judge_query(provider, text, proposal['sql'], result, selected)
        calls.append(judge_meta)
        semantic = validated_judgement(judged)
        history.append({'sql': proposal['sql'], 'checks': semantic})
        if any((check['result'] == 'FAIL' for check in semantic)):
            repaired, repair_meta = gateway.repair_query(provider, text, proposal['sql'], semantic, selected)
            calls.append(repair_meta)
            proposal['sql'] = repaired['sql']
            result = gateway.query_rows(proposal['sql'], {entry['table'] for entry in selected})
            judged, judge_meta = gateway.judge_query(provider, text, proposal['sql'], result, selected)
            calls.append(judge_meta)
            semantic = validated_judgement(judged)
            history.append({'sql': proposal['sql'], 'checks': semantic, 'changed_reason': repaired['changed_reason']})
    meta = combine_metrics(calls)
    meta['context_level'] = context_level
    meta['semantic_verification_enabled'] = verify
    if result['truncated']:
        meta['warnings'].append('행 상한까지 표시했습니다. 전체 집계는 SQL 집계로 다시 확인하세요')
    checks = [{'item': '열 번호가 등록되어 있음', 'result': 'PASS'}, {'item': '읽기 전용 SQL 계약', 'result': 'PASS'}, {'item': '사람의 최종 검토', 'result': 'UNKNOWN'}]
    checks += semantic
    answer = {**result, 'sql': proposal['sql'], 'checks': checks, 'repair_history': history, 'judgement_score': sum((check['result'] == 'PASS' for check in semantic)), 'judgement_total': len(semantic), 'probe': probes, 'context': {'sql': proposal['sql'], 'profile': profile, 'source_ids': source_ids}}
    evidence = [{'kind': 'table', 'ref': ', '.join(source_ids), 'sql': proposal['sql'], 'rows': len(result['rows']), 'provenance': [x['provenance'] for x in selected]}]
    if any((check['result'] != 'PASS' for check in semantic)):
        return reply(rid, {'sql': proposal['sql'], 'checks': checks, 'repair_history': history}, status='failed', reason='대상·범위·계산·의미의 확인이 끝나지 않았습니다. 답변으로 공개하지 않았습니다', meta=meta)
    meta['warnings'].append('모델 심사 통과는 실제 정답 보증이 아닙니다. 표와 질문을 대조하세요' if verify else '모델 의미 심사를 끈 비교 실행입니다. 사람이 직접 표와 질문을 대조하세요')
    return reply(rid, answer, status='ok' if result['rows'] else 'none', evidence=evidence, reason='' if result['rows'] else '조건에 맞는 행이 없습니다', meta=meta)

def validated_judgement(value: dict) -> list[dict]:
    checks = value.get('checks', [])
    if len(checks) != 4 or {item.get('item') for item in checks} != {'target', 'scope', 'calculation', 'meaning'}:
        raise ValueError('심사 항목이 누락되거나 중복됐습니다')
    if any((item.get('result') not in {'PASS', 'FAIL', 'UNKNOWN'} for item in checks)):
        raise ValueError('심사 상태가 계약과 다릅니다')
    return checks

def series(rid: str, profile: str, source_id: str, column_id: int, lot_id: str | None):
    config = analysis_source(source_id, profile)
    columns = {c['id']: c for c in config['columns']}
    if column_id not in columns or columns[column_id]['type'] != 'number':
        raise ValueError('등록된 수치 열을 선택하세요')
    from psycopg import sql
    condition = sql.SQL('') if lot_id is None else sql.SQL(' WHERE lot_id={}').format(sql.Literal(lot_id))
    query = sql.SQL('SELECT row_no,lot_id,{} AS value FROM lab.{}{} ORDER BY row_no').format(sql.Identifier(f'c{column_id}'), sql.Identifier(config['table']), condition).as_string()
    result = gateway.query_rows(query, {config['table']})
    return reply(rid, {**result, 'column': columns[column_id], 'axis': '파일 행 순서', 'provenance': config['provenance']}, status='ok' if result['rows'] else 'none', reason='' if result['rows'] else '표시할 행 없음', evidence=[{'kind': 'table', 'ref': source_id, 'sql': query, 'rows': len(result['rows'])}])

def quality(rid: str, profile: str, source_id: str):
    from psycopg import sql
    config = source(source_id, profile)
    projections = [sql.SQL('count(*) AS total')]
    numeric = [c for c in config['columns'] if c['type'] == 'number']
    for column in numeric:
        name = sql.Identifier(f"c{column['id']}")
        for label, expression in [('missing', sql.SQL('count(*) FILTER (WHERE {} IS NULL)')), ('zero', sql.SQL('count(*) FILTER (WHERE {}=0)')), ('negative', sql.SQL('count(*) FILTER (WHERE {}<0)')), ('min', sql.SQL('min({})')), ('max', sql.SQL('max({})'))]:
            projections.append(sql.SQL('{} AS {}').format(expression.format(name), sql.Identifier(f"{column['id']}_{label}")))
    statement = sql.SQL('SELECT {} FROM lab.{}').format(sql.SQL(',').join(projections), sql.Identifier(config['table'])).as_string()
    result = gateway.query_rows(statement, {config['table']})
    return reply(rid, {'statistics': result['rows'], 'columns': numeric, 'note': '0·음수·최댓값은 관측값입니다. 삭제 사유나 고장 원인 판정이 아닙니다.'}, evidence=[{'kind': 'table', 'ref': source_id, 'sql': statement, 'rows': 1}])

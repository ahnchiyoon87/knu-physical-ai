"""리허설 기록 준비·검사·집계. 네트워크 연결이나 모델 호출을 하지 않는다."""
from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import argparse
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / '작업기록/실습측정'
PATHS = {'coding', 'hydops_agent', 'platform_agent', 'embedding_index', 'embedding_query'}
SCOPES = {'student_once', 'session_recurring', 'shared_setup', 'extra_practice'}
STATUSES = {'success', 'failed', 'cancelled', 'unknown'}


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'), parse_float=Decimal)


def save(path, data):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def initialize(session_id, participant_id, trial_id, files):
    for value in (participant_id, trial_id):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
            raise ValueError('참여자·시험 ID는 익명 영문/숫자/하이픈/밑줄로 지정하세요.')
    slots = read_json(TEMPLATES / '회차별_측정틀.json')['records']
    matches = [x for x in slots if x['school_session_id'] == session_id]
    if len(matches) != 1:
        raise ValueError('학교 회차 ID를 확인하세요: 실1~실9 또는 통1~통10')
    snapshots = []
    for file in files:
        file = file.resolve()
        if not file.is_relative_to(ROOT) or not file.is_file():
            raise ValueError('해시 대상은 프로젝트 안의 실제 파일이어야 합니다.')
        if '.runtime' in file.parts or file.name.startswith('.env'):
            raise ValueError('비밀 저장 파일은 입력 기록 대상이 아닙니다.')
        snapshots.append({'path':file.relative_to(ROOT).as_posix(),
                          'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    if not snapshots:
        raise ValueError('가이드·시작 코드·입력의 실제 파일을 --file로 지정하세요.')
    destination = ROOT / '.runtime/measurements' / trial_id
    destination.mkdir(parents=True, exist_ok=False)
    slot = matches[0]
    slot.update({'trial_id':trial_id, 'participant_id':participant_id,
                 'source_revision':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip(),
                 'request_records_path':'requests.jsonl', 'file_snapshots':snapshots,
                 'prepared_at':datetime.now(timezone.utc).isoformat()})
    # Preparation is not the beginning of a timed student rehearsal.
    save(destination / 'session.json', slot)
    template = read_json(TEMPLATES / '요청기록_양식.json')
    template.pop('request_path_allowed', None)
    template.pop('notes', None)
    template.update({'trial_id':trial_id,'participant_id':participant_id,
                     'school_session_id':session_id})
    save(destination / 'request-template.json', template)
    (destination / 'requests.jsonl').touch(exist_ok=False)
    (destination / 'evidence').mkdir()
    return destination


def amount(value, field):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f'{field}: bool은 금액이 아닙니다.')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f'{field}: 숫자 또는 null이어야 합니다.') from None
    if not number.is_finite() or number < 0:
        raise ValueError(f'{field}: 유한한 0 이상 금액이어야 합니다.')
    return number


def summarize(folder):
    session = read_json(folder / 'session.json')
    template = read_json(TEMPLATES / '요청기록_양식.json')
    allowed = set(template) - {'request_path_allowed', 'notes'}
    seen = set()
    groups = {}
    count = 0
    for line_no, line in enumerate((folder / 'requests.jsonl').read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line, parse_float=Decimal)
        if not isinstance(record, dict) or set(record) - allowed:
            raise ValueError(f'{line_no}행: 허용된 요청 메타데이터 필드만 기록하세요.')
        if record.get('record_kind') != '실측':
            raise ValueError(f'{line_no}행: 양식이나 합성 예시를 실제 요청으로 집계하지 않습니다.')
        for field in ('trial_id','participant_id','school_session_id'):
            if record.get(field) != session.get(field):
                raise ValueError(f'{line_no}행: {field}가 리허설과 다릅니다.')
        if record.get('request_path') not in PATHS or record.get('cost_scope') not in SCOPES:
            raise ValueError(f'{line_no}행: 호출 경로와 비용 범위를 확인하세요.')
        if record.get('status') not in STATUSES:
            raise ValueError(f'{line_no}행: 실제 요청 결과 상태를 확인하세요.')
        for field in ('logical_task_id','actual_provider_model_id','provider_name'):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f'{line_no}행: {field}가 필요합니다.')
        if type(record.get('attempt')) is not int or record['attempt'] < 1:
            raise ValueError(f'{line_no}행: attempt는 1부터 세는 실제 시도 번호입니다.')
        for field in ('input_tokens','cached_input_tokens','output_tokens','reasoning_tokens'):
            value = record.get(field)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f'{line_no}행: {field}는 0 이상 정수 또는 null이어야 합니다.')
        for field in ('queue_wait_ms','time_to_first_token_ms','total_request_ms'):
            amount(record.get(field), field)
        for field in ('started_at','finished_at'):
            stamp = datetime.fromisoformat(record[field])
            if stamp.tzinfo is None:
                raise ValueError(f'{line_no}행: 시간대가 필요합니다.')
        if datetime.fromisoformat(record['finished_at']) < datetime.fromisoformat(record['started_at']):
            raise ValueError(f'{line_no}행: 종료 시각이 시작보다 빠릅니다.')
        evidence = (folder / record['evidence_path']).resolve()
        if not evidence.is_relative_to(folder.resolve()) or not evidence.is_file():
            raise ValueError(f'{line_no}행: 시험 폴더 안의 실제 증거 파일이 필요합니다.')
        if not record.get('evidence_record_id'):
            raise ValueError(f'{line_no}행: 증거 안의 행 번호/고유 항목 ID가 필요합니다.')
        identities = [('evidence', str(evidence), str(record['evidence_record_id']))]
        if record.get('provider_request_id'):
            identities.append(('provider',record['provider_name'],record['provider_request_id']))
        if record.get('gateway_request_id'):
            identities.append(('gateway',record['gateway_request_id'],record['attempt']))
        if any(key in seen for key in identities):
            raise ValueError(f'{line_no}행: 같은 과금 요청 또는 증거 항목이 중복됐습니다.')
        seen.update(identities)
        key = (record['request_path'],record['cost_scope'],record['provider_name'],record['actual_provider_model_id'])
        group = groups.setdefault(key, {'requests':0,'non_success':0,
            'provider_billed_usd':[], 'proxy_estimated_usd':[]})
        group['requests'] += 1
        group['non_success'] += record['status'] != 'success'
        for field in ('provider_billed_usd','proxy_estimated_usd'):
            group[field].append(amount(record.get(field), field))
        count += 1
    result = {'trial_id':session['trial_id'], 'requests':count,
              'status':'미측정' if not count else '기록 집계', 'groups':[],
              'scope':'제공사 확인 금액과 중계 추정액은 별도 집계. 과정 총비용·학생 완주·청구 정합성의 증거가 아님.'}
    for key, group in sorted(groups.items()):
        row = dict(zip(('request_path','cost_scope','provider_name','actual_provider_model_id'), key))
        row.update({'requests':group['requests'], 'non_success':group['non_success']})
        for field in ('provider_billed_usd','proxy_estimated_usd'):
            values = group[field]
            known = [x for x in values if x is not None]
            row[field] = {'known_subtotal':str(sum(known, Decimal(0))) if known else None,
                          'unknown_requests':len(values)-len(known),
                          'complete_total':str(sum(known, Decimal(0))) if len(known)==len(values) else None}
        result['groups'].append(row)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='새 리허설 폴더 준비')
    init.add_argument('session_id')
    init.add_argument('participant_id')
    init.add_argument('trial_id')
    init.add_argument('--file', type=Path, action='append', required=True)
    report = sub.add_parser('summary', help='실제 요청 기록 검사·집계')
    report.add_argument('folder', type=Path)
    report.add_argument('--output', type=Path, help='새 JSON 결과 파일. 기존 파일 덮어쓰기 금지')
    args = parser.parse_args()
    if args.command == 'init':
        print(initialize(args.session_id,args.participant_id,args.trial_id,args.file))
    else:
        result = summarize(args.folder)
        if args.output:
            save(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))

"""제공 1~4일차 코드와 실제 평가·DB 읽기를 이용한 체크포인트 검사.

학생이 만든 코드의 완주 검사가 아니다. 출력은 새 폴더만 사용한다.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from 체크포인트_저장 import save, verify, digest
from hydops.b3_tsdb import store


def main(root, output, run_id):
    output.mkdir(parents=True, exist_ok=False)
    files = sorted(p for day in range(1, 5)
                   for p in (root/f'실습자료/{day}일차/완성본').rglob('*')
                   if p.is_file() and p.suffix in {'.py', '.ipynb'} and '.ipynb_checkpoints' not in p.parts)

    def snapshot():
        with store.connect() as connection:
            connection.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
            rows = {table: connection.execute(f'SELECT * FROM {table} WHERE run_id=%s ORDER BY 1', (run_id,)).fetchall()
                    for table in ('run', 'event')}
            rows['history'] = connection.execute('SELECT h.* FROM event_history h JOIN event e ON e.event_id=h.event_id WHERE e.run_id=%s ORDER BY h.id', (run_id,)).fetchall()
        return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()

    before = snapshot()
    target = output/'저장본'
    save(target, files, run_id, root/'실습자료', [[4, 3, 10, 5], [2, 1, 1, 1], [4, 3, 1, 5], [4, 3, 20, 5]])
    result = verify(target)
    manifest = json.loads((target/'checkpoint.json').read_text(encoding='utf-8'))
    assert len({p.name for p in files}) < len(files), '같은 이름을 포함한 시험이어야 합니다.'
    assert {p.split('/')[0] for p in [item['path'] for item in manifest['files']]} == {'1일차', '2일차', '3일차', '4일차'}
    evaluations = manifest['phase_evaluations']
    assert [(r['fp'], r['mean_delay_s']) for r in evaluations] == [(1, 9.0), (4, 0.0), (1, 0.0), (1, 19.0)]
    after = snapshot()
    assert before == after
    checks = []

    def rejected(label, fn):
        try:
            fn()
        except (ValueError, FileExistsError, FileNotFoundError) as error:
            checks.append({'case': label, 'rejected': True, 'error': str(error)})
        else:
            raise AssertionError(label+'가 거부되지 않았습니다.')

    original_hash = digest(target/'checkpoint.json')
    rejected('기존 저장본 덮어쓰기', lambda: save(target, files, run_id, root/'실습자료'))
    assert original_hash == digest(target/'checkpoint.json')
    rejected('공통 경로 없이 같은 파일명', lambda: save(output/'중복', files, run_id))
    rejected('공통 경로 밖 코드', lambda: save(output/'경로밖', files, run_id, root/'실습자료/4일차'))
    rejected('잘못된 비교 구간', lambda: save(output/'잘못된설정', files, run_id, root/'실습자료', [[4, 3, 1.5, 5]]))
    rejected('존재하지 않는 실행', lambda: save(output/'없는실행', files, 'CHECKPOINT-NONEXISTENT', root/'실습자료'))
    assert not any((output/name).exists() for name in ['중복', '경로밖', '잘못된설정', '없는실행'])

    # 의도적으로 망가뜨린 별도 사본에서 검사기가 실제로 실패하는지 확인한다.
    with tempfile.TemporaryDirectory() as temp:
        broken = Path(temp)/'복사본'
        shutil.copytree(target, broken)
        code = broken/manifest['files'][0]['path']
        code.write_bytes(code.read_bytes()+b'\n# changed\n')
        rejected('저장 코드 변조', lambda: verify(broken))
        shutil.copy2(target/manifest['files'][0]['path'], code)
        for label, change in [
            ('시험 ID 변조', lambda m: m['test_ids'].append(999999)),
            ('평가 사이클 변조', lambda m: m['phase_evaluations'][0]['rows'][0].update(cycle=999999)),
            ('다른 실행의 사건', lambda m: m['events'][0].update(run_id='OTHER')),
            ('상위 경로 참조', lambda m: m['files'][0].update(path='../outside.py')),
        ]:
            current = json.loads((target/'checkpoint.json').read_text(encoding='utf-8'))
            change(current)
            (broken/'checkpoint.json').write_text(json.dumps(current), encoding='utf-8')
            rejected(label, lambda: verify(broken))

    summary = {'scope': '제공 완성본 1~4일차 저장·실제 UCI 평가·지정 DB 사건 읽기. 학생 완주·DB 복원 아님.',
               'result': result, 'checks': checks, 'db_before_sha256': before, 'db_after_sha256': after,
               'evaluations': [{k: v for k, v in r.items() if k != 'rows'} for r in evaluations],
               'saved_code_days': [1, 2, 3, 4], 'duplicate_basenames_preserved': True}
    (output/'검증결과.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    main(args.root, args.output, args.run_id)

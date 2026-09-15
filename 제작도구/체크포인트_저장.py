"""지정한 코드·설정·시험 구간·실행 기록을 새 폴더에 저장한다.

제공 플랫폼을 불러올 수 있는 Python 환경에서 실행한다.
DB는 읽기만 한다. 이 도구는 DB 자동 복원을 수행하지 않는다.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify(output):
    """저장 파일과 기록의 대응을 검사한다. 실행 환경이나 DB를 복원하지 않는다."""
    output = output.resolve(strict=True)
    manifest = json.loads((output/'checkpoint.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        relative = Path(item.get('path', item.get('name', '')))
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('체크포인트 밖의 파일 경로입니다.')
        target = (output/relative).resolve(strict=True)
        if not target.is_relative_to(output) or digest(target) != item['sha256']:
            raise ValueError('저장 코드의 위치 또는 해시가 다릅니다.')
    tests = manifest['test_ids']
    if hashlib.sha256(json.dumps(tests).encode()).hexdigest() != manifest['test_ids_sha256']:
        raise ValueError('시험 ID 해시가 다릅니다.')
    if set(tests) & set(manifest['baseline_ids']):
        raise ValueError('기준과 시험 구간이 겹칩니다.')
    for result in manifest.get('phase_evaluations', []):
        if [row['cycle'] for row in result['rows']] != tests:
            raise ValueError('평가 결과의 시험 ID가 다릅니다.')
        if result['test_cycles'] != len(tests) or result['baseline_cycles'] != len(manifest['baseline_ids']):
            raise ValueError('평가 구간 수가 다릅니다.')
    run_id = manifest['run']['run_id']
    event_ids = {e['event_id'] for e in manifest['events']}
    if any(e['run_id'] != run_id for e in manifest['events']) or any(h['event_id'] not in event_ids for h in manifest['history']):
        raise ValueError('다른 실행의 사건 또는 이력이 섞였습니다.')
    return {'code_files': len(manifest['files']), 'phase_comparisons': len(manifest.get('phase_evaluations', [])),
            'test_cycles': len(tests), 'events': len(event_ids), 'history': len(manifest['history']),
            'scope': '저장 코드 해시·구간·사건 연결 확인. DB 복원 및 코드 재실행 아님.'}


def save(output, files, run_id, root=None, comparisons=None):
    from hydops.config import TH, QR, DATA_DIR
    from hydops.b5_detect import evaluate
    from hydops.b3_tsdb import store

    output = output.resolve()
    resolved = [p.resolve(strict=True) for p in files]
    if not resolved:
        raise ValueError('저장할 코드를 지정하세요.')
    root = root.resolve(strict=True) if root else None
    for p in resolved:
        if not p.is_file() or p.suffix not in {'.py', '.ipynb'}:
            raise ValueError('명시한 Python 코드와 노트북만 저장합니다.')
    names = [p.relative_to(root).as_posix() if root else p.name for p in resolved]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError('저장 경로가 중복됩니다. --root로 개인 작업의 공통 폴더를 지정하세요.')
    if output.exists():
        raise FileExistsError('기존 체크포인트는 보존합니다. 새 폴더를 지정하세요.')
    configs = []
    for values in comparisons or []:
        if len(values) != 4 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError('비교 설정은 양의 유한수 네 개여야 합니다.')
        k, delta, sustain, smooth = values
        if int(sustain) != sustain or int(smooth) != smooth or sustain > 60 or smooth > 60:
            raise ValueError('지속·평활 구간은 1~60의 정수로 지정하세요.')
        configs.append(dict(k_sigma=k, min_delta_c=delta, sustain_s=int(sustain), smooth_s=int(smooth)))
    ds, baseline, test_ids = evaluate.fixed_split()
    tests = [int(x) for x in test_ids]
    results = [evaluate.evaluate(**config) for config in configs]
    with store.connect() as c:
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        run = c.execute('SELECT * FROM run WHERE run_id=%s', (run_id,)).fetchone()
        if run is None:
            raise ValueError('지정한 run_id가 없습니다.')
        events = c.execute('SELECT * FROM event WHERE run_id=%s ORDER BY event_id', (run_id,)).fetchall()
        history = c.execute('SELECT h.* FROM event_history h JOIN event e ON h.event_id=e.event_id WHERE e.run_id=%s ORDER BY h.event_id,h.id', (run_id,)).fetchall()
        c.execute('COMMIT')
    manifest = {
        'format_version': 2,
        'saved_at': datetime.now(timezone.utc).isoformat(),
        'scope': '코드·설정·시험 구간·지정 실행의 사건/이력 보존. DB 복원·학생 완주 검증 아님.',
        'thresholds': asdict(TH), 'quality_rules': asdict(QR),
        'settings_scope': '저장 시 불러온 플랫폼 기본값. 지정 run이나 학생 코드가 실제 사용한 설정임을 증명하지 않는다.',
        'phase_evaluation_scope': '명시한 비교값으로 제공 evaluate.evaluate를 지금 실행한 결과. 학생 수정 코드의 결과 또는 지정 run의 설정과 구분한다.',
        'phase_evaluations': results,
        'split_seed': evaluate.SPLIT_SEED,
        'baseline_ids': [int(x) for x in baseline], 'test_ids': tests,
        'test_ids_sha256': hashlib.sha256(json.dumps(tests).encode()).hexdigest(),
        'dataset_files': {str(p.relative_to(DATA_DIR)): digest(p) for p in sorted((DATA_DIR/'reduced').glob('*')) if p.is_file()},
        'files': [{'path': name, 'sha256': digest(p)} for p, name in zip(resolved, names)],
        'run': run, 'events': events, 'history': history,
    }
    output.mkdir(parents=True)
    for src, name in zip(resolved, names):
        (output/name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, output/name)
    for item in manifest['files']:
        assert digest(output/item['path']) == item['sha256']
    path = output/'checkpoint.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    reread = json.loads(path.read_text(encoding='utf-8'))
    assert reread['test_ids'] == tests and reread['run']['run_id'] == run_id
    print(json.dumps(verify(output), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--file', type=Path, action='append')
    parser.add_argument('--run-id')
    parser.add_argument('--root', type=Path, help='회차 폴더를 포함한 개인 작업의 공통 상위 경로')
    parser.add_argument('--compare', type=float, nargs=4, action='append', metavar=('SIGMA', 'DELTA_C', 'SUSTAIN_S', 'SMOOTH_S'), help='제공 평가를 이 설정으로 실행·저장. 여러 번 지정 가능')
    parser.add_argument('--verify', action='store_true', help='이미 저장한 폴더를 DB 연결 없이 검사')
    args = parser.parse_args()
    if args.verify:
        if args.file or args.run_id or args.root or args.compare:
            parser.error('--verify는 저장 옵션과 함께 쓰지 않습니다.')
        print(json.dumps(verify(args.output), ensure_ascii=False))
    else:
        if not args.file or not args.run_id:
            parser.error('저장에는 --file과 --run-id가 필요합니다.')
        save(args.output, args.file, args.run_id, args.root, args.compare)

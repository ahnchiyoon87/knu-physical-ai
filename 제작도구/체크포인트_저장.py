"""지정한 코드·설정·시험 구간·실행 기록을 새 폴더에 저장한다.

제공 플랫폼을 불러올 수 있는 Python 환경에서 실행한다.
DB는 읽기만 한다. 이 도구는 DB 자동 복원을 수행하지 않는다.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from hydops.config import TH, QR, DATA_DIR
from hydops.b5_detect import evaluate
from hydops.b3_tsdb import store


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save(output, files, run_id):
    output = output.resolve()
    resolved = [p.resolve(strict=True) for p in files]
    for p in resolved:
        if not p.is_file() or p.suffix not in {'.py', '.ipynb'}:
            raise ValueError('명시한 Python 코드와 노트북만 저장합니다.')
    if len({p.name for p in resolved}) != len(resolved):
        raise ValueError('파일 이름이 중복됩니다. 회차별로 별도 저장하세요.')
    if output.exists():
        raise FileExistsError('기존 체크포인트는 보존합니다. 새 폴더를 지정하세요.')
    ds, baseline, test_ids = evaluate.fixed_split()
    tests = [int(x) for x in test_ids]
    with store.connect() as c:
        c.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        run = c.execute('SELECT * FROM run WHERE run_id=%s', (run_id,)).fetchone()
        if run is None:
            raise ValueError('지정한 run_id가 없습니다.')
        events = c.execute('SELECT * FROM event WHERE run_id=%s ORDER BY event_id', (run_id,)).fetchall()
        history = c.execute('SELECT h.* FROM event_history h JOIN event e ON h.event_id=e.event_id WHERE e.run_id=%s ORDER BY h.event_id,h.id', (run_id,)).fetchall()
        c.execute('COMMIT')
    manifest = {
        'saved_at': datetime.now(timezone.utc).isoformat(),
        'scope': '코드·설정·시험 구간·지정 실행의 사건/이력 보존. DB 복원·학생 완주 검증 아님.',
        'thresholds': asdict(TH), 'quality_rules': asdict(QR),
        'split_seed': evaluate.SPLIT_SEED,
        'baseline_ids': [int(x) for x in baseline], 'test_ids': tests,
        'test_ids_sha256': hashlib.sha256(json.dumps(tests).encode()).hexdigest(),
        'dataset_files': {str(p.relative_to(DATA_DIR)): digest(p) for p in sorted((DATA_DIR/'reduced').glob('*')) if p.is_file()},
        'files': [{'name': p.name, 'sha256': digest(p)} for p in resolved],
        'run': run, 'events': events, 'history': history,
    }
    output.mkdir(parents=True)
    for src in resolved:
        shutil.copy2(src, output/src.name)
    for item in manifest['files']:
        assert digest(output/item['name']) == item['sha256']
    path = output/'checkpoint.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    reread = json.loads(path.read_text(encoding='utf-8'))
    assert reread['test_ids'] == tests and reread['run']['run_id'] == run_id
    print(json.dumps({'code_files': len(resolved), 'baseline_cycles': len(baseline), 'test_cycles': len(tests), 'events': len(events), 'history': len(history), 'test_ids_sha256': manifest['test_ids_sha256']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--file', type=Path, action='append', required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    save(args.output, args.file, args.run_id)

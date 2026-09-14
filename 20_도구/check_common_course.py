"""Check shared edition coverage, source ranges and actual full/part/script text."""
import copy
import hashlib
import json
from build_common_course import ROOT, MANIFEST, UNITS, render


def check_structure(record):
    expected = [list(u[1]) for u in UNITS]
    if [u['keys'] for u in record['units']] != expected:
        raise ValueError('공통 필수 주제가 누락되거나 순서가 다릅니다')
    paths = [u['deck'] for u in record['units']]
    if any(p != paths for p in record['cohorts'].values()) or len(record['cohorts']) != 2:
        raise ValueError('두 반이 같은 공통 내용을 사용하지 않습니다')


def main():
    record = json.loads(MANIFEST.read_text(encoding='utf-8'))
    check_structure(record)
    broken = copy.deepcopy(record)
    next(u for u in broken['units'] if 'G' in u['keys'])['keys'].remove('G')
    try:
        check_structure(broken)
    except ValueError:
        pass
    else:
        raise AssertionError('주제 누락을 놓쳤습니다')
    broken = copy.deepcopy(record); next(iter(broken['cohorts'].values())).pop()
    try:
        check_structure(broken)
    except ValueError:
        pass
    else:
        raise AssertionError('반별 내용 차이를 놓쳤습니다')
    for name, expected in record['files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    for source in record['sources']:
        for kind in ('deck', 'script'):
            assert hashlib.sha256((ROOT / source[kind]).read_bytes()).hexdigest() == source[kind + '_sha256']
    for name, expected in record.get('editorial_sources', {}).items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    for u in record['units']:
        full = (ROOT / u['deck']).read_text(encoding='utf-8')
        script = (ROOT / u['script']).read_text(encoding='utf-8')
        assert script == render(u['title'], u['slides'], True)
        assert full.startswith(render(u['title'], u['slides']))
        assert '## 제작 참고 출처' in full
        footer = full[len(render(u['title'], u['slides'])):]
        for i, path in enumerate(u['parts']):
            assert (ROOT / path).read_text(encoding='utf-8') == render(u['title'], u['slides'][i*12:(i+1)*12]) + footer
        assert len({s['id'] for s in u['slides']}) == len(u['slides'])
    result = {'units': len(record['units']), 'slides': sum(len(u['slides']) for u in record['units']),
              'files': len(record['files']), 'same_cohort_paths': True, 'missing_topic_and_cohort_mismatch_rejected': True,
              'scope': '공통 필수 주제 목록·같은 파일 연결·출처 파일 해시·전체/분할/대본 문구 검사. 전 장 의미·시간·실습 배정 검증 아님'}
    (ROOT / '30_기록/공통강의_구조검사.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

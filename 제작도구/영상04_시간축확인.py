"""제공 원본·설정·축약 함수를 영상04의 상대 시간 설명과 대조한다.

정밀 수집 시각이나 실제 센서 동기화 검증이 아니다. DB 연결 없이 실행한다.
"""
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

root, output = map(Path, sys.argv[1:3])
if output.exists():
    raise FileExistsError(output)
source = root / '실습자료/1일차/완성본/practical/mapping.py'
spec = importlib.util.spec_from_file_location('course_mapping', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from hydops.b1_data import uci

records = []
for sid, hz in [('TS1', 1), ('FS1', 10), ('PS1', 100)]:
    assert module.SENSOR_SPEC[sid]['hz'] == uci.SENSOR_MAP[sid]['hz'] == hz
    raw_path = module.RAW / module.SENSOR_SPEC[sid]['file']
    samples = module.read_raw_cycle(sid, 100)
    with raw_path.open(encoding='ascii') as f:
        line = next(line for n, line in enumerate(f) if n == 100)
    direct = [float(s) for s in line.rstrip().split('\t')]
    assert samples.tolist() == direct and len(samples) == hz * 60
    # Fraction prevents a floating-point rounding accident at a boundary.
    times = [Fraction(i, hz) for i in range(len(samples))]
    groups = [[i for i, t in enumerate(times) if second <= t < second + 1]
              for second in range(60)]
    assert [i for group in groups for i in group] == list(range(len(samples)))
    assert all(len(group) == hz for group in groups)
    assert groups[10] == list(range(10 * hz, 11 * hz))
    practical = module.reduce_to_seconds(samples, hz)
    platform = uci.reduce_to_1s(samples.reshape(1, -1), hz)
    for second, indexes in enumerate(groups):
        values = samples[indexes]
        expected = {'mean': float(values.mean()), 'min': float(values.min()),
                    'max': float(values.max()), 'n': len(indexes)}
        assert practical[second] == expected
        assert all(float(platform[key][0, second]) == value for key, value in expected.items())
    # Alternative wrong axis is caught by step and sample-count checks.
    inclusive_end_step = Fraction(60, len(samples) - 1)
    assert inclusive_end_step != Fraction(1, hz)
    exact_position = Fraction(1005, 100) * hz
    records.append({
        'sensor': sid, 'hz': hz, 'samples': len(samples),
        'raw_sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        'relative_step_s': str(Fraction(1, hz)),
        'index10_relative_s': str(times[10]),
        'index_at_10s': 10 * hz, 'value_at_10s': direct[10 * hz],
        'last_index': len(samples) - 1, 'last_relative_s': str(times[-1]),
        'position_at_10_05s': str(exact_position),
        'has_sample_at_10_05s': exact_position.denominator == 1,
        'second10_indices': [groups[10][0], groups[10][-1]],
        'all_60_groups_cover_each_sample_once': True,
        'all_60_groups_match_practical_and_platform': True,
        'wrong_inclusive_60_endpoint_rejected': True,
    })
assert [r['has_sample_at_10_05s'] for r in records] == [False, False, True]
assert len({r['index10_relative_s'] for r in records}) == 3
result = {'scope': '원본 사이클100과 제공 함수, 첫 샘플0초의 상대 시간 계산. 실제 수집 시각·센서 동기화·학생 완주 검증 아님.',
          'mapping_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'records': records}
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))

"""영상05의 묶기/선택 구분과 실제 원본 경계를 DB 없이 검증한다."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

root, output = map(Path, sys.argv[1:3])
if output.exists():
    raise FileExistsError(output)


def load(relative, name):
    path = root / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


solution, source = load('실습자료/1일차/완성본/practical/mapping.py', 'solution')
starter, starter_path = load('실습자료/1일차/원문시작본/practical/mapping.py', 'starter')
source_text = source.read_text(encoding='utf-8')
tree = ast.parse(source_text)
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'reduce_to_seconds')
assignment = next(n for n in function.body if isinstance(n, ast.Assign))
snippet = ast.get_source_segment(source_text, assignment)
assert snippet == 'shaped = samples.reshape(CYCLE_S, hz)'


def group(samples, hz):
    scope = {'samples': samples, 'CYCLE_S': solution.CYCLE_S, 'hz': hz}
    exec(snippet, scope)
    return scope['shaped']


def check_groups(original, grouped, hz):
    assert grouped.shape == (60, hz), 'wrong number/size of groups'
    assert np.array_equal(grouped.reshape(-1), original), 'values or sequence changed'
    for second in range(60):
        expected = original[second * hz:(second + 1) * hz]
        assert np.array_equal(grouped[second], expected), 'wrong time boundary'


records = []
for sid, hz in [('TS1', 1), ('FS1', 10), ('PS1', 100)]:
    samples = solution.read_raw_cycle(sid, 100)
    before = samples.copy()
    shaped = group(samples, hz)
    check_groups(samples, shaped, hz)
    # Position labels are synthetic index probes, not pressure/temperature values.
    positions = np.arange(60 * hz)
    check_groups(positions, group(positions, hz), hz)
    st = starter.reduce_to_seconds(samples, hz)
    sol = solution.reduce_to_seconds(samples, hz)
    assert len(st) == len(sol) == 60
    assert all(row['n'] == 1 for row in st)
    assert all(row['n'] == hz for row in sol)
    assert all(st[s]['mean'] == float(shaped[s, 0]) for s in range(60))
    rejected = []
    for delta in [-1, 1]:
        broken = samples[:-1] if delta == -1 else np.append(samples, samples[-1])
        try:
            solution.reduce_to_seconds(broken, hz)
        except ValueError as e:
            rejected.append({'count': len(broken), 'message': str(e)})
        else:
            raise AssertionError('wrong sample count accepted')
    assert np.array_equal(samples, before)
    records.append({'sensor': sid, 'cycle': 100, 'input_shape': list(samples.shape),
                    'grouped_shape': list(shaped.shape), 'all_values_in_order': True,
                    'all_60_boundaries_match': True, 'position_probe_pass': True,
                    'selected_groups': [{'second': s, 'first_index': s*hz, 'last_index': (s+1)*hz-1,
                                         'count': int(shaped[s].size), 'first_value': float(shaped[s,0]),
                                         'last_value': float(shaped[s,-1])} for s in [0,1,59]],
                    'starter_outputs': len(st), 'solution_outputs': len(sol),
                    'starter_n': st[0]['n'], 'solution_n': sol[0]['n'],
                    'bad_lengths_rejected': rejected, 'input_unchanged': True})

positions = np.arange(6000)
bad_groups = {
    '100_by_60': positions.reshape(100, 60),
    'first_sample_only': positions.reshape(60, 100)[:, :1],
    'wrong_column_order': positions.reshape(60, 100, order='F'),
    'one_position_shift': np.roll(positions, 1).reshape(60, 100),
}
rejections = {}
for name, wrong in bad_groups.items():
    try:
        check_groups(positions, wrong, 100)
    except AssertionError as e:
        rejections[name] = str(e)
    else:
        raise AssertionError('bad grouping passed: '+name)
result = {'scope': '사이클100 실제 샘플과 제공 코드 묶기·선택 비교. 위치번호 반증은 합성 검사 입력이며 센서 실측이 아니다.',
          'executed_snippet': snippet, 'solution_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'starter_sha256': hashlib.sha256(starter_path.read_bytes()).hexdigest(),
          'records': records, 'bad_groupings_rejected': rejections}
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'sensors':len(records), 'bad_lengths_rejected':6, 'bad_groupings_rejected':rejections}, ensure_ascii=False))

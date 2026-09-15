"""영상03에 쓰는 원본 위치와 제공 함수 출력을 대조한다. DB 연결 없음."""
import importlib.util
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
output = Path(sys.argv[2])
if output.exists():
    raise FileExistsError(output)
source = root/'실습자료/1일차/완성본/practical/mapping.py'
spec = importlib.util.spec_from_file_location('course_mapping', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
records = []
for sensor, width in [('TS1', 60), ('FS1', 600), ('PS1', 6000)]:
    direct = {}
    with (module.RAW/(sensor+'.txt')).open(encoding='ascii') as stream:
        for physical_line, line in enumerate(stream, 1):
            if physical_line in (100, 101, 102):
                direct[physical_line] = [float(x) for x in line.rstrip().split('\t')]
            if physical_line == 102:
                break
    for cycle in (99, 100, 101):
        values = module.read_raw_cycle(sensor, cycle)
        assert len(values) == width and values.tolist() == direct[cycle+1]
        records.append({'sensor': sensor, 'cycle_index': cycle, 'physical_line': cycle+1,
                        'sample_count': len(values), 'first_value': float(values[0]), 'whole_row_equal': True})
assert [r['first_value'] for r in records if r['sensor'] == 'TS1'] == [53.324, 53.219, 53.379]
assert module.read_raw_cycle('TS1', 100).tolist() != module.read_raw_cycle('TS1', 99).tolist()
result = {'scope': '제공 함수의 실제 원본 읽기와 독립 줄 조회 대조. DB·UI·학생완주 검증 아님.',
          'records': records, 'adjacent_cycle_is_different': True}
output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))

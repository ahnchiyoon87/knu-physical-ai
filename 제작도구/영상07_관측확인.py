"""실제 map_cycle의180개 관측을 원본 구간·출처와 대조한다. DB 사용 없음."""
from collections import Counter
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

root, out = map(Path, sys.argv[1:3])
out.mkdir(parents=True, exist_ok=False)
path=root/'실습자료/1일차/완성본/practical/mapping.py'
spec=importlib.util.spec_from_file_location('mapping',path)
mapping=importlib.util.module_from_spec(spec);spec.loader.exec_module(mapping)
raw={sid:mapping.read_raw_cycle(sid,100) for sid in mapping.SENSOR_SPEC}
rows=mapping.map_cycle(raw,100,'HYD-01',mapping.LAB_REPLAY_START)
expected={}
for sid,hz,unit in [('TS1',1,'°C'),('PS1',100,'bar'),('FS1',10,'L/min')]:
    with (root/f'플랫폼코드/data/raw/{sid}.txt').open(encoding='ascii') as stream:
        line=next(line for i,line in enumerate(stream) if i==100)
    values=[Decimal(v) for v in line.rstrip().split('\t')]
    for second in range(60):
        group=values[second*hz:(second+1)*hz]
        expected[sid,second]={'mean':float(sum(group)/hz),'min':float(min(group)),
                              'max':float(max(group)),'n':hz,'unit':unit}


def verify(records):
    assert len(records)==180
    seen=set()
    for row in records:
        assert set(row)=={'asset_id','sensor_id','ts','elapsed_s','origin_cycle_id','raw_value','unit','agg','is_synthetic'}
        key=row['sensor_id'],row['elapsed_s']
        assert key in expected and key not in seen
        seen.add(key);e=expected[key]
        assert row['asset_id']=='HYD-01' and row['origin_cycle_id']==100
        assert row['is_synthetic'] is False and row['unit']==e['unit']
        assert row['ts']==mapping.LAB_REPLAY_START+timedelta(seconds=key[1])
        assert math.isclose(row['raw_value'],e['mean'],rel_tol=0,abs_tol=1e-10)
        if e['n']==1:
            assert row['agg'] is None
        else:
            assert row['agg']=={'min':round(e['min'],4),'max':round(e['max'],4),'n':e['n'],'source_hz':e['n']}
    assert seen==set(expected)


verify(rows)
psindex=next(i for i,r in enumerate(rows) if r['sensor_id']=='PS1' and r['elapsed_s']==0)
changes={
    'missing_unit':lambda r:r.pop('unit'),
    'wrong_unit':lambda r:r.update(unit='°C'),
    'wrong_cycle':lambda r:r.update(origin_cycle_id=99),
    'wrong_synthetic':lambda r:r.update(is_synthetic=True),
    'first_value_instead_of_mean':lambda r:r.update(raw_value=float(raw['PS1'][0])),
    'wrong_replay_time':lambda r:r.update(ts=r['ts']+timedelta(seconds=1)),
    'missing_aggregation':lambda r:r.update(agg=None),
}
rejected=[]
for name,change in changes.items():
    altered=deepcopy(rows);change(altered[psindex])
    try:verify(altered)
    except AssertionError:rejected.append(name)
    else:raise AssertionError(name)
json_rows=[{**row,'ts':row['ts'].isoformat()} for row in rows]
(out/'관측.json').write_text(json.dumps(json_rows,ensure_ascii=False,indent=2),encoding='utf-8')
result={'records':len(rows),'per_sensor':dict(Counter(r['sensor_id'] for r in rows)),
        'field_count':9,'all_raw_groups_match':True,'abs_tolerance':1e-10,
        'selected_records':[r for r in json_rows if r['elapsed_s'] in (0,59)],
        'bad_records_rejected':rejected,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'scope':'원본 사이클100을 map_cycle로 변환한 품질검사 전180개. DB적재·관제·학생완주 검증 아님.'}
(out/'대조.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ['records','per_sensor','bad_records_rejected']},ensure_ascii=False))

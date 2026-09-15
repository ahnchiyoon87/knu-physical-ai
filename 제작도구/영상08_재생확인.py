"""실제 매핑 함수의 세 사이클 재생 시각을 확인한다. DB 적재는 하지 않는다."""
from collections import Counter
from copy import deepcopy
from datetime import timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

root,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
path=root/'실습자료/1일차/완성본/practical/mapping.py'
spec=importlib.util.spec_from_file_location('mapping',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
start=m.LAB_REPLAY_START
assert start.isoformat()=='2026-09-01T00:00:00+00:00'
rows=[]
for i,cid in enumerate([100,101,102]):
    raw={sid:m.read_raw_cycle(sid,cid) for sid in m.SENSOR_SPEC}
    rows.extend(m.map_cycle(raw,cid,'HYD-01',start+timedelta(seconds=i*m.CYCLE_S)))


def check(records):
    assert len(records)==540
    actual={}
    for row in records:
        key=row['sensor_id'],row['origin_cycle_id'],row['elapsed_s']
        assert key not in actual
        expected_seconds=(key[1]-100)*60+key[2]
        assert row['ts']==start+timedelta(seconds=expected_seconds)
        assert 0<=key[2]<60
        actual[key]=row
    for sid in ['TS1','FS1','PS1']:
        selected=sorted([r for r in records if r['sensor_id']==sid],key=lambda r:r['ts'])
        assert len(selected)==180
        assert [int((r['ts']-start).total_seconds()) for r in selected]==list(range(180))
        assert [r['elapsed_s'] for r in selected]==list(range(60))*3


check(rows)
bad=[]
for name in ['reset_time_each_cycle','continuous_elapsed','wrong_origin']:
    changed=deepcopy(rows)
    for row in changed:
        if name=='reset_time_each_cycle':row['ts']=start+timedelta(seconds=row['elapsed_s'])
        elif name=='continuous_elapsed':row['elapsed_s']=int((row['ts']-start).total_seconds())
        elif row['origin_cycle_id']==101:row['origin_cycle_id']=100
    try:check(changed)
    except AssertionError:bad.append(name)
    else:raise AssertionError(name)
shifted=[]
for i,cid in enumerate([100,101,102]):
    raw={sid:m.read_raw_cycle(sid,cid) for sid in m.SENSOR_SPEC}
    shifted.extend(m.map_cycle(raw,cid,'HYD-01',start+timedelta(hours=1,seconds=i*60)))
for a,b in zip(rows,shifted):
    assert b['ts']-a['ts']==timedelta(hours=1)
    assert {k:v for k,v in a.items() if k!='ts'}=={k:v for k,v in b.items() if k!='ts'}
selected=[r for r in rows if r['sensor_id']=='PS1' and r['elapsed_s'] in (0,59)]
serialize=lambda r:{**r,'ts':r['ts'].isoformat()}
result={'scope':'원본3사이클과 실제 map_cycle로 재생 시각을 구성. load_cycles/DB적재 실행 아님.',
        'start':start.isoformat(),'records':len(rows),'per_sensor':dict(Counter(r['sensor_id'] for r in rows)),
        'boundaries':[serialize(r) for r in selected],'bad_timeline_rejected':bad,
        'shift_start_preserves_source_and_values':True,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(out/'재생대조.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'records':len(rows),'boundaries':[{k:r[k] for k in ['origin_cycle_id','elapsed_s','ts']} for r in result['boundaries']],'bad_timeline_rejected':bad},ensure_ascii=False))

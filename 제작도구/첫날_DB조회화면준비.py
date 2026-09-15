"""실전 완성본의 실제 DB 적재·조회 결과를 검토용 노트북에 기록한다."""
from pathlib import Path
import json
import shutil
import subprocess
import uuid

root=Path(__file__).resolve().parents[1]
work=root/'작업기록/첫날제작_20260915/노트북실제화면_v1/실전조회'
work.mkdir(exist_ok=False)
shutil.copy2(root/'실습자료/1일차/완성본/practical/mapping.py',work/'mapping.py')
cells=[]
def add(kind,text):
    c={'id':uuid.uuid4().hex[:8],'cell_type':kind,'metadata':{},'source':text.splitlines(True)}
    if kind=='code':c.update(execution_count=None,outputs=[])
    cells.append(c)
add('markdown','# 실행 구간과 원본 사이클 확인\n\n실전 코드의 실행 결과를 표로 확인합니다. 재생 시각은 실습용이며 실제 수집 날짜가 아닙니다.')
add('code','''import sys, uuid, json
from pathlib import Path
from datetime import timedelta
import pandas as pd
sys.path.insert(0, '/course/플랫폼코드')
import mapping as m
from hydops.b3_tsdb import store

run_id = 'LAB-S01-VIEW-' + uuid.uuid4().hex[:8]
count = m.load_cycles(run_id, [100, 101, 102])
assert count == 540
print('실행 ID:', run_id)
print('적재 관측:', count)
''')
add('code','''# 마지막 60초 조회
last = m.window_with_origin(run_id, 'HYD-01', 60)
summary=[]
for sid, data in last['sensors'].items():
    assert data['samples']==60 and data['origin_cycles']==[102]
    assert sorted(data['elapsed'])==list(range(60))
    assert data['run_ids']==[run_id] and data['is_synthetic']==[False]
    summary.append({'센서':sid,'단위':data['unit'],'관측 수':data['samples'],
                    '원본 사이클':102,'경과 초':f"{min(data['elapsed'])}~{max(data['elapsed'])}",
                    '합성 여부':False})
print('대상:',run_id,'/ HYD-01')
display(pd.DataFrame(summary))
''')
add('code','''# 사이클 경계의 60초 조회
until = m.LAB_REPLAY_START + timedelta(seconds=90)
rows = store.recent_window('HYD-01',60,run_id=run_id,until=until)
frame=pd.DataFrame(rows)
boundary=frame.groupby(['sensor_id','origin_cycle_id']).agg(
    관측수=('elapsed_s','size'),시작초=('elapsed_s','min'),끝초=('elapsed_s','max')).reset_index()
assert len(rows)==180 and set(frame.run_id)=={run_id}
for _, row in boundary.iterrows():
    expected=(29,31,59) if row.origin_cycle_id==100 else (31,0,30)
    assert (row.관측수,row.시작초,row.끝초)==expected
print('재생 시작+90초를 끝으로 하는 60초 /',run_id)
display(boundary.rename(columns={'sensor_id':'센서','origin_cycle_id':'원본 사이클'}))
Path('조회결과.json').write_text(json.dumps({'run_id':run_id,'inserted':count,'last':summary,
    'boundary':boundary.to_dict(orient='records')},ensure_ascii=False,indent=2),encoding='utf-8')
''')
add('code','''# 압력 첫1초의 원본과 집계 비교
raw=m.read_raw_cycle('PS1',100)[:100]
reduced=m.reduce_to_seconds(m.read_raw_cycle('PS1',100),100)[0]
assert reduced['n']==100
display(pd.DataFrame([{'사이클':100,'구간':'첫1초','첫 샘플':float(raw[0]),
    '평균':reduced['mean'],'최솟값':reduced['min'],'최댓값':reduced['max'],'샘플 수':reduced['n'],'단위':'bar'}]))
''')
notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}
(work/'DB조회_입력.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=2),encoding='utf-8')
cmd=['docker','run','--rm','--network','knu-hydops-local_default',
     '-e','HYDOPS_AGENT_MODE=offline','-e','HYDOPS_PG_DSN=postgresql://hydops:hydops@postgres:5432/hydops',
     '--mount',f'type=bind,source={root/"플랫폼코드"},target=/course/플랫폼코드,readonly',
     '--mount',f'type=bind,source={work},target=/course/student-work','-w','/course/student-work',
     'knu-hydops-notebook-ui:review','jupyter','nbconvert','--execute','--to','notebook',
     'DB조회_입력.ipynb','--output','DB조회_결과.ipynb']
r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
(work/'실행기록.json').write_text(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},ensure_ascii=False,indent=2),encoding='utf-8')
if r.returncode:raise SystemExit(r.stderr)
print((work/'조회결과.json').read_text(encoding='utf-8'))

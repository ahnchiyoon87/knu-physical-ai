"""둘째 날 실제 완성 코드·DB 조회 결과를 캡처용 노트북으로 실행한다."""
from pathlib import Path
import json
import shutil
import subprocess
import uuid

root = Path(__file__).resolve().parents[1]
work = root/'작업기록/첫날제작_20260915/노트북실제화면_v1/둘째날품질조회'
work.mkdir(exist_ok=False)
for source, target in [('integrated/quality_lab.py','quality_lab.py'),
                       ('practical/quality.py','quality.py'),
                       ('practical/test_check.py','practical_tests.py')]:
    shutil.copy2(root/'실습자료/2일차/완성본'/source,work/target)
cells=[]


def add(kind, body):
    cell={'id':uuid.uuid4().hex[:8],'cell_type':kind,'metadata':{},'source':body.splitlines(True)}
    if kind=='code': cell.update(execution_count=None,outputs=[])
    cells.append(cell)


add('markdown','# 품질 표시와 판단할 값\n\n실제 과제 코드의 실행·DB 재조회 결과입니다. UCI 원본의 오류 주입 복사본과 교육용 시뮬레이터를 구분합니다.')
add('code','''import sys, json
from pathlib import Path
import pandas as pd
import numpy as np
sys.path.insert(0, '/course/플랫폼코드')
import quality_lab as lab
import quality as practical
import practical_tests
from hydops.b1_data import uci
from hydops.b2_quality.checks import window_quality, classify_window

original=uci.cycle_observations(uci.load_reduced(),1500,'HYD-01',lab.REPLAY_START)
injected=lab.make_injected_rows()
checked=lab.check_rows(injected)
other=practical.LabQualityChecker().check_many(injected)
assert checked==other, '반별 실제 품질 결과 불일치'
run_id=lab.new_run_id()
inserted=lab.load_to_db(run_id,checked)
assert inserted==180
fetched=lab.last_60s(run_id)
assert len(fetched)==60 and {r['origin_cycle_id'] for r in fetched}=={1500}
assert sum(r['raw_value'] is None for r in fetched)==7
assert sum(r['value'] is None for r in fetched)==11
print('DB 실행:',run_id,'/ HYD-01 / 원본 사이클1500 / 적재180행 / TS1 조회60행')
''')
add('code','''# 원본과 오류 주입 복사본
o={r['elapsed_s']:r['raw_value'] for r in original if r['sensor_id']=='TS1'}
i={r['elapsed_s']:r['raw_value'] for r in injected if r['sensor_id']=='TS1'}
before=[{'경과 초':s,'원본 온도':o[s],'오류 주입 후':i[s]} for s in [18,19,20,25,26,27,42,43,44]]
print('TS1 / °C / 사이클1500 · 원본 파일은 바꾸지 않았습니다.')
display(pd.DataFrame(before).fillna('비어 있음'))
''')
add('code','''# 품질 표시와 DB에 남은 값
selected=[r for r in fetched if r['elapsed_s'] in [18,19,20,26,29,30,32,49,50,52,53]]
display(pd.DataFrame([{'경과 초':r['elapsed_s'],'검사 전 값':r['raw_value'],
                       '판단할 값':r['value'],'품질 표시':r['quality_flag']} for r in selected]).fillna('비어 있음'))
counts=[{'센서':sid,**lab.flag_counts(checked,sid)} for sid in ['TS1','PS1','FS1']]
print('전체60초의 센서별 표시 개수')
display(pd.DataFrame(counts).fillna(0).set_index('센서').astype(int))
''')
add('code','''# 같은 실행에서 구간별 판단
ranges=[('전체',0,59),('비교 A',5,9),('비교 B',17,21),('비교 C',28,32)]
range_results=[]
for label,start,end in ranges:
    part=lab.range_rows(run_id,(start,end))
    q=window_quality(part)
    range_results.append({'구간':label,'경과 초':f'{start}~{end}','관측 수':q['n'],
                          '품질 표시':str(q['flags']),'결과':classify_window(part,lab.RULES)})
assert [r['결과'] for r in range_results]==['SENSOR_FAULT','VALID','VALID','SENSOR_FAULT']
range_table=[]
for item, (_,start,end) in zip(range_results,ranges):
    flags=window_quality(lab.range_rows(run_id,(start,end)))['flags']
    range_table.append({'구간':item['구간'],'경과 초':item['경과 초'],
                        **{flag:flags.get(flag,0) for flag in ['OK','SPIKE','MISSING','GAP','STUCK']},
                        '결과':item['결과']})
display(pd.DataFrame(range_table))
print('VALID는 선택한 구간의 센서 품질 결과입니다. 설비 정상 판정이 아닙니다.')
''')
add('code','''# 결측 샘플의 1초 집계
from hydops.config import DATA_DIR
from itertools import islice
with open(DATA_DIR/'raw/PS1.txt') as f:
    samples=np.array(next(islice(f,100,101)).split(),dtype=float)
modified=samples.copy()
modified[500:600]=np.nan
modified[600:670]=np.nan
modified[700:720]=np.nan
seconds=practical.aggregate_1s(modified,100)
assert [seconds[s]['n'] for s in [5,6,7,8]]==[0,30,80,100]
assert seconds[5]['mean'] is None and seconds[6]['mean'] is None
display(pd.DataFrame([{'경과 초':s,'유효 샘플':seconds[s]['n'],'평균 [bar]':seconds[s]['mean']}
                     for s in [5,6,7,8]]).fillna('비어 있음'))
print('PS1 · 원본 사이클100의 복사본에 결측 주입 · 1초당100샘플 · 최소50개 필요')
''')
add('code','''# 냉각 변화와 센서 고착
sim_results=[]
for label,fault in [('냉각 심각 저하',None),('냉각 저하 뒤 고착','stuck')]:
    sim_rows=practical.LabQualityChecker().check_many(practical_tests._severe_degradation(fault))
    part=sim_rows[-60:]
    state=practical.window_state(part)
    sim_results.append({'사례':label,'최근 관측 수':len(part),'SPIKE 수':sum(r['quality_flag']=='SPIKE' for r in sim_rows),
                        '최근60초 STUCK 수':sum(r['quality_flag']=='STUCK' for r in part),'결과':state['state']})
assert [r['결과'] for r in sim_results]==['EQUIPMENT_ANOMALY','SENSOR_FAULT']
display(pd.DataFrame(sim_results))
print('교육용 시뮬레이터 · 동일 시드7 · 냉각 효율0.25 · 실제 설비 측정 결과 아님')
result={'run_id':run_id,'inserted':inserted,'database_rows':fetched,'flags':counts,
        'ranges':range_results,'simulator':sim_results,'cohort_quality_outputs_equal':True}
_ = Path('검증결과.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
''')
notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}
(work/'품질_입력.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=2),encoding='utf-8')
cmd=['docker','run','--rm','--network','knu-hydops-local_default',
     '-e','HYDOPS_AGENT_MODE=offline','-e','HYDOPS_PG_DSN=postgresql://hydops:hydops@postgres:5432/hydops',
     '--mount',f'type=bind,source={root/"플랫폼코드"},target=/course/플랫폼코드,readonly',
     '--mount',f'type=bind,source={work},target=/course/student-work','-w','/course/student-work',
     'knu-hydops-notebook-ui:review','jupyter','nbconvert','--execute','--to','notebook',
     '품질_입력.ipynb','--output','품질_결과.ipynb']
result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
(work/'실행기록.json').write_text(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},ensure_ascii=False,indent=2),encoding='utf-8')
if result.returncode: raise SystemExit(result.stderr)
print('둘째 날 실제 코드·DB 조회 노트북 실행 완료:',work)

"""실제 사건 인용·ID 되돌리기·그래프와 관측 결합을 확인한다. 유료 호출 없음."""
from pathlib import Path
import json
import shutil
import subprocess
import uuid

root=Path(__file__).resolve().parents[1]
work=root/'작업기록/첫날제작_20260915/노트북실제화면_v1/셋째날관계조회'
work.mkdir(exist_ok=False)
for folder,name in [('integrated','graph_lab.py'),('practical','context_queries.py')]:
    shutil.copy2(root/'실습자료/3일차/완성본'/folder/name,work/name)
cells=[]


def add(kind,text):
    cell={'id':uuid.uuid4().hex[:8],'cell_type':kind,'metadata':{},'source':text.splitlines(True)}
    if kind=='code':cell.update(execution_count=None,outputs=[])
    cells.append(cell)


add('markdown','# 관계와 측정값을 함께 확인하기\n\n제공 과제 코드·Neo4j·PostgreSQL의 실제 결과를 확인합니다. 인용 존재와 승인·조치 완료를 구분합니다.')
add('code','''import sys,json,hashlib
from pathlib import Path
import pandas as pd
sys.path.insert(0,'/course/플랫폼코드')
import graph_lab as lab
import context_queries as practical
from hydops.b4_ontology import graph
from hydops.b3_tsdb import store

def graph_hash():
    nodes=graph.run('MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS properties ORDER BY id')
    rels=graph.run('MATCH ()-[r]->() RETURN elementId(r) AS id, type(r) AS type, properties(r) AS properties ORDER BY id')
    return hashlib.sha256(json.dumps([nodes,rels],sort_keys=True,default=str).encode()).hexdigest()
before=graph_hash()
event_id='EVT-20270126-090043-HYD-01-e51b'
event=lab.run_read(lab.Q_EVENT_EVIDENCE,event_id=event_id)
assert len(event)==1 and len(event[0]['citations'])>0, '사전 인용 사건을 먼저 확인하세요.'
print('준비 사건:',event_id)
print('설비:',event[0]['asset_id'],'/ 유형:',event[0]['event_type'],'/ 상태:',event[0]['status'])
''')
add('code','''# 사건이 인용한 문서의 판과 절
citations=graph.run("""MATCH (e:Event {event_id:$id})-[:CITES]->(sec:SOPSection)<-[:HAS_SECTION]-(sop:SOP)
RETURN sop.doc_id AS document,sop.version AS version,sec.section_no AS section,sec.heading AS heading
ORDER BY document,version,section""",id=event_id)
assert len(citations)==len(event[0]['citations'])
display(pd.DataFrame(citations).rename(columns={'document':'문서 ID','version':'판','section':'절','heading':'제목'}))
print('사건 상태:',event[0]['status'],'· 인용 조회만 수행했습니다.')
''')
add('code','''# 같은 ID와 잘못된 ID의 차이
for sensor in graph.SENSORS:
    current=graph.run('MATCH (s:Sensor {sensor_id:$id}) RETURN properties(s) AS p',id='HYD-01.'+sensor['code'])
    assert len(current)==1 and all(current[0]['p'].get(k)==v for k,v in sensor.items()), '기존 센서 변경을 보존해야 하므로 시험 중지'
same=lab.seed_check()
assert len(same)==4 and all(r['committed'] and r['nodes_created']==r['relationships_created']==0 for r in same)
display(pd.DataFrame([{'대상':r['what'],'새 노드':r['nodes_created'],'새 관계':r['relationships_created'],'반영':r['committed']} for r in same]))
assert graph.run('MATCH (s:Sensor {sensor_id:$id}) RETURN count(s) AS n',id='HYD-01-TS1')[0]['n']==0
wrong=lab.merge_if_same_as_seed(lab.MERGE_SENSOR.replace("+ '.' +", "+ '-' +"),asset_id='HYD-01',**graph.SENSORS[0])
remaining=graph.run('MATCH (s:Sensor {sensor_id:$id}) RETURN count(s) AS n',id='HYD-01-TS1')[0]['n']
assert wrong['nodes_created']==1 and wrong['relationships_created']==1 and not wrong['committed'] and remaining==0
display(pd.DataFrame([{'시험 ID':'HYD-01-TS1','생성될 노드':wrong['nodes_created'],'생성될 관계':wrong['relationships_created'],
                      '반영':wrong['committed'],'되돌린 뒤 노드':remaining}]))
''')
add('code','''# 그래프의 센서와 DB의 최근 관측 연결
run_id=lab.load_lab_cycle()
try:
    joined=lab.sensors_with_recent_values('HYD-01',run_id)
    practical_result=practical.join_recent('HYD-01',run_id)
    assert len(joined)==3 and all(r['n']==r['valid']==60 and r['origin_cycle_id']==100 for r in joined)
    assert all(r['unit_graph']==r['unit_db'] for r in joined)
    assert len(practical_result['sensors'])==3 and all(r['samples']==60 and r['unit_match'] for r in practical_result['sensors'])
    print('실습 실행:',run_id,'/ HYD-01 / UCI 사이클100')
    display(pd.DataFrame(joined).rename(columns={'sensor_id':'그래프 센서 ID','unit_graph':'그래프 단위','unit_db':'DB 단위',
          'n':'관측 수','valid':'품질 OK','last_value':'마지막 원시값','origin_cycle_id':'원본 사이클'}))
    wrong_key=store.recent_window('HYD-01',60,sensor_id='HYD-01.TS1',run_id=run_id)
    right_key=store.recent_window('HYD-01',60,sensor_id='TS1',run_id=run_id)
    assert len(wrong_key)==0 and len(right_key)==60
    display(pd.DataFrame([{'설비 조건':'HYD-01','센서 조건':key,'조회 행':n} for key,n in [('HYD-01.TS1',len(wrong_key)),('TS1',len(right_key))]]))
    _ = Path('관계와최근값.json').write_text(json.dumps({'run_id':run_id,'integrated':joined,'practical':practical_result},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
finally:
    lab.cleanup(run_id)
''')
add('code','''# 결과 파일 다시 열기와 내 임시 실행 정리
saved=json.loads(Path('관계와최근값.json').read_text(encoding='utf-8'))
assert saved['integrated']==joined and saved['run_id']==run_id
with store.connect() as connection:
    left=connection.execute('SELECT count(*) AS n FROM observation WHERE run_id=%s',(run_id,)).fetchone()['n']
    run_left=connection.execute('SELECT count(*) AS n FROM run WHERE run_id=%s',(run_id,)).fetchone()['n']
assert left==run_left==0
after=graph_hash()
assert before==after, '그래프 전후 내용이 달라졌습니다. 원인 확인 필요.'
assert event==lab.run_read(lab.Q_EVENT_EVIDENCE,event_id=event_id)
print('다시 읽은 결과:',len(saved['integrated']),'센서 / 각각60개 관측 / 원본 사이클100')
print('정리한 실습 실행:',run_id)
print('DB에 남은 해당 실행:',run_left,'/ 관측:',left)
print('기존 사건 상태·인용 동일 / 그래프 전후 내용 해시 동일')
record={'event':event,'citations':citations,'same_ids':same,'wrong_id':wrong,'wrong_id_after':remaining,
        'joined':joined,'run_id':run_id,'run_remaining':run_left,'observations_remaining':left,
        'saved_result_reopened':True,'graph_before_sha256':before,'graph_after_sha256':after}
_ = Path('검증결과.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
''')
notebook={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}
(work/'관계_입력.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=2),encoding='utf-8')
cmd=['docker','run','--rm','--network','knu-hydops-local_default',
     '-e','HYDOPS_AGENT_MODE=offline','-e','HYDOPS_PG_DSN=postgresql://hydops:hydops@postgres:5432/hydops',
     '-e','HYDOPS_NEO4J_URI=bolt://neo4j:7687',
     '--mount',f'type=bind,source={root/"플랫폼코드"},target=/course/플랫폼코드,readonly',
     '--mount',f'type=bind,source={work},target=/course/student-work','-w','/course/student-work',
     'knu-hydops-notebook-ui:review','jupyter','nbconvert','--execute','--to','notebook','관계_입력.ipynb','--output','관계_결과.ipynb']
r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
(work/'실행기록.json').write_text(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},ensure_ascii=False,indent=2),encoding='utf-8')
if r.returncode: raise SystemExit(r.stderr)
print('실제 사건 인용·ID 되돌리기·최근 관측 결합·파일 재열기 확인:',work)

"""Use the provided save path in an isolated local database; verify in a new process."""
from pathlib import Path
import sys,json,importlib.util
from copy import deepcopy
from datetime import timedelta
from collections import Counter
import psycopg
from hydops.b3_tsdb import store
from hydops.b2_quality.checks import SensorQualityChecker
from hydops.config import SETTINGS
root,out=map(Path,sys.argv[1:3]);phase=sys.argv[3]
assert SETTINGS.pg_dsn.endswith("/hydops_v10_review"), "Dedicated review DB required"
run_id="LAB-V10-STORAGE"
source=root/"실습자료/1일차/완성본/practical/mapping.py"
spec=importlib.util.spec_from_file_location("mapping",source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def normalize(value):
 return json.loads(json.dumps(value,default=lambda x:x.isoformat(),ensure_ascii=False))
if phase=="save":
 out.mkdir(parents=True,exist_ok=False)
 store.init_schema(reset=False)
 with store.connect() as c:
  assert c.execute("SELECT count(*) AS n FROM run").fetchone()["n"]==0
 count=m.load_cycles(run_id,[100,101,102])
 assert count==540
 (out/"저장.json").write_text(json.dumps({"run_id":run_id,"returned_count":count,"scope":"actual load_cycles into dedicated DB"}),encoding="utf-8")
 print("Saved 540 observations through provided load_cycles")
elif phase=="read":
 with store.connect() as c:
  c.execute("BEGIN READ ONLY")
  actual=c.execute("SELECT * FROM observation WHERE run_id=%s ORDER BY ts,sensor_id",(run_id,)).fetchall()
  execution=c.execute("SELECT run_id,source,scenario FROM run WHERE run_id=%s",(run_id,)).fetchone()
  c.execute("COMMIT")
 checker=SensorQualityChecker();expected=[]
 for i,cid in enumerate([100,101,102]):
  raw={sid:m.read_raw_cycle(sid,cid) for sid in m.SENSOR_SPEC}
  expected.extend(checker.check_many(m.map_cycle(raw,cid,"HYD-01",m.LAB_REPLAY_START+timedelta(seconds=i*60))))
 assert len(actual)==len(expected)==540
 assert execution=={"run_id":run_id,"source":"uci_replay","scenario":"lab-s01"}
 for a,b in zip(actual,expected):
  assert normalize({k:a[k] for k in b})==normalize(b)
  assert a["run_id"]==run_id
 assert len({a["id"] for a in actual})==540
 (out/"재조회.json").write_text(json.dumps({"scope":"fresh process, read-only query, all540 compared to recomputed source","run":execution,"count":len(actual),"per_sensor":dict(Counter(r["sensor_id"] for r in actual)),"all_original_fields_match":True,"sample":normalize(actual[1])},ensure_ascii=False,indent=2),encoding="utf-8")
 print("Fresh process: all 540 stored rows match regenerated source fields")
elif phase=="constraints":
 checker=SensorQualityChecker();raw={sid:m.read_raw_cycle(sid,100) for sid in m.SENSOR_SPEC}
 rows=checker.check_many(m.map_cycle(raw,100,"HYD-01",m.LAB_REPLAY_START))
 bad=deepcopy(rows[:2]);bad[1]["unit"]=None
 checks=[]
 for name,rid,data,error in [("missing_run","LAB-V10-NOT-CREATED",rows[:1],psycopg.errors.ForeignKeyViolation),("null_unit_second_row",run_id,bad,psycopg.errors.NotNullViolation)]:
  try:store.insert_observations(rid,data)
  except error:checks.append(name)
  else:raise AssertionError(name)
 with store.connect() as c:
  count=c.execute("SELECT count(*) AS n FROM observation WHERE run_id=%s",(run_id,)).fetchone()["n"]
 assert count==540
 (out/"제약확인.json").write_text(json.dumps({"rejected":checks,"count_after_failures":count,"scope":"one COPY statement rollback; does not prove entire load_cycles atomic"},ensure_ascii=False,indent=2),encoding="utf-8")
 print("Rejected unknown run and missing unit; original540 preserved")
else:raise ValueError(phase)

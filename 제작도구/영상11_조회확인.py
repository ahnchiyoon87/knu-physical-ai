"""Query the provided store against the isolated review DB; preserve original run."""
from pathlib import Path
from datetime import timedelta
from collections import Counter
import sys,json,hashlib,importlib.util
from hydops.b3_tsdb import store
from hydops.config import SETTINGS
root,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
assert SETTINGS.pg_dsn.endswith("/hydops_v10_review")
primary="LAB-V10-STORAGE";other="LAB-V11-OTHER"
source=root/"실습자료/1일차/완성본/practical/mapping.py"
spec=importlib.util.spec_from_file_location("mapping",source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def read_all(rid):
 with store.connect() as c:
  c.execute("BEGIN READ ONLY")
  rows=c.execute("SELECT * FROM observation WHERE run_id=%s ORDER BY ts,sensor_id",(rid,)).fetchall()
  c.execute("COMMIT")
 return rows
def digest(rows):return hashlib.sha256(json.dumps(rows,default=str,sort_keys=True).encode()).hexdigest()
base=read_all(primary);assert len(base)==540;before=digest(base)
assert not read_all(other), "Other run already exists: inspect instead of appending"
assert m.load_cycles(other,[100,101,102],start=m.LAB_REPLAY_START+timedelta(hours=1))==540
cases={}
def compare(name,rows,expected):
 assert [{k:r[k] for k in rows[0]} for r in expected]==rows if rows else not expected
 cases[name]={"count":len(rows),"run_ids":sorted({r["run_id"] for r in rows}),"cycles":dict(Counter(r["origin_cycle_id"] for r in rows)),"per_sensor":dict(Counter(r["sensor_id"] for r in rows)),"first":rows[0]["ts"].isoformat() if rows else None,"last":rows[-1]["ts"].isoformat() if rows else None}
end=m.LAB_REPLAY_START+timedelta(seconds=179)
compare("latest_all",store.recent_window("HYD-01",run_id=primary),[r for r in base if r["ts"]>end-timedelta(seconds=60)])
compare("latest_ps1",store.recent_window("HYD-01",sensor_id="PS1",run_id=primary),[r for r in base if r["ts"]>end-timedelta(seconds=60) and r["sensor_id"]=="PS1"])
boundary=m.LAB_REPLAY_START+timedelta(seconds=90)
expected=[r for r in base if boundary-timedelta(seconds=60)<r["ts"]<=boundary]
compare("boundary",store.recent_window("HYD-01",run_id=primary,until=boundary),expected)
assert cases["boundary"]["cycles"]=={100:87,101:93}
compare("missing_run",store.recent_window("HYD-01",run_id="LAB-V11-NOT-FOUND"),[])
other_rows=read_all(other);last=other_rows[-1]["ts"]
compare("without_run",store.recent_window("HYD-01"),[r for r in other_rows if r["ts"]>last-timedelta(seconds=60)])
assert cases["without_run"]["run_ids"]==[other]
with store.connect() as c:
 c.execute("BEGIN READ ONLY")
 inclusive=c.execute("SELECT count(*) AS n FROM observation WHERE run_id=%s AND ts >= %s AND ts <= %s",(primary,boundary-timedelta(seconds=60),boundary)).fetchone()["n"]
 c.execute("COMMIT")
assert inclusive==183 and cases["boundary"]["count"]==180
assert digest(read_all(primary))==before
result={"cases":cases,"inclusive_lower_bound_count":inclusive,"wrong_boundary_detected":True,"primary_run_unchanged":True,"primary_sha256":before,"scope":"actual store functions, isolated DB; added other replay run540; no source/runtime app changes"}
(out/"조회대조.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))

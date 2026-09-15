"""Verify provided quality outputs, without DB writes or model calls."""
from pathlib import Path
import sys,json,hashlib,importlib.util
from copy import deepcopy
from datetime import timedelta
from collections import Counter
from hydops.b2_quality.checks import SensorQualityChecker
root,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
source=root/"실습자료/1일차/완성본/practical/mapping.py"
spec=importlib.util.spec_from_file_location("mapping",source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checker=SensorQualityChecker();original=[];checked=[]
for i,cid in enumerate([100,101,102]):
 raw={sid:m.read_raw_cycle(sid,cid) for sid in m.SENSOR_SPEC}
 rows=m.map_cycle(raw,cid,"HYD-01",m.LAB_REPLAY_START+timedelta(seconds=i*60))
 original.extend(deepcopy(rows));checked.extend(checker.check_many(rows))
lookup={(r["sensor_id"],r["ts"]):r for r in original}
for row in checked:
 before=lookup[row["sensor_id"],row["ts"]]
 assert {k:row[k] for k in before}==before
 assert row["value"]==(row["raw_value"] if row["quality_flag"]=="OK" else None)
assert Counter(r["quality_flag"] for r in checked)=={"OK":540}
examples={}
for name,values,expected in [("OK",[53.0,53.2],"OK"),("SPIKE",[53.0,80.0],"SPIKE"),("MISSING",[53.0,None],"MISSING"),("GAP",[None]*5,"GAP"),("STUCK",[53.0]*8,"STUCK"),("OUT_OF_RANGE",[-20.0],"OUT_OF_RANGE")]:
 c=SensorQualityChecker();samples=[]
 for second,value in enumerate(values):
  row={"asset_id":"EXAMPLE","sensor_id":"TS1","ts":m.LAB_REPLAY_START+timedelta(seconds=second),"raw_value":value,"unit":"°C"}
  samples.append(c.check(row))
 assert samples[-1]["quality_flag"]==expected
 assert samples[-1]["raw_value"]==values[-1]
 assert samples[-1]["value"]==(values[-1] if expected=="OK" else None)
 if name=="STUCK": assert samples[0]["quality_flag"]=="OK"
 examples[name]={"kind":"설명용 입력을 제공 검사기로 실행","inputs":values,"first":samples[0],"last":samples[-1]}
serialize=lambda obj:obj.isoformat() if hasattr(obj,"isoformat") else str(obj)
result={"scope":"Real UCI540 and separate illustrative TS1 sequences; no DB or inference","uci_flags":dict(Counter(r["quality_flag"] for r in checked)),"source_fields_preserved":True,"examples":examples,"checker_sha256":hashlib.sha256((root/"플랫폼코드/hydops/b2_quality/checks.py").read_bytes()).hexdigest()}
(out/"품질대조.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,default=serialize),encoding="utf-8")
print(json.dumps({"uci_flags":result["uci_flags"],"examples":{k:v["last"]["quality_flag"] for k,v in examples.items()}},ensure_ascii=False))

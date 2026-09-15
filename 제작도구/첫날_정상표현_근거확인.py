"""원문 데이터와 B2 원본 함수를 분리 실행한다. DB/모델/전체 실습은 실행하지 않는다."""
from pathlib import Path
import ast
from array import array
from zipfile import ZipFile
import struct
import sys
import types
import importlib.util
import json
import hashlib
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / 'lecture-manufacturing-physical-ai-platform/system'
OUT = ROOT / '작업기록/첫날제작_20260915'
OUT.mkdir(parents=True, exist_ok=True)

def npy_float(data):
    assert data[:6] == b'\x93NUMPY'
    major = data[6]
    size = 2 if major == 1 else 4
    n = int.from_bytes(data[8:8+size], 'little')
    header = ast.literal_eval(data[8+size:8+size+n].decode('latin1'))
    assert header['descr'] in ('<f8', '<f4'), header
    a = array('d' if header['descr']=='<f8' else 'f')
    a.frombytes(data[8+size+n:])
    if sys.byteorder != 'little': a.byteswap()
    shape = header['shape']
    assert len(shape)==2 and len(a)==shape[0]*shape[1]
    if header['fortran_order']:
        return [[a[j*shape[0]+i] for j in range(shape[1])] for i in range(shape[0])]
    return [a[i*shape[1]:(i+1)*shape[1]] for i in range(shape[0])]

profile = [[int(x) for x in line.split()] for line in (SRC/'data/raw/profile.txt').read_text().splitlines()]
with ZipFile(SRC/'data/reduced/hydraulic_1s.npz') as z:
    means={s:npy_float(z.read(s+'_mean.npy')) for s in ('TS1','PS1','FS1')}
assert all(len(v)==len(profile)==2205 for v in means.values())

# .env/서비스 의존성을 불러오지 않고 원문 QualityRules 정의를 그대로 사용한다.
config_path=SRC/'hydops/config.py'
tree=ast.parse(config_path.read_text(encoding='utf-8'))
quality=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='QualityRules')
cfg=types.ModuleType('hydops.config')
sys.modules['hydops.config']=cfg
exec('from dataclasses import dataclass, field',cfg.__dict__)
exec(compile(ast.Module(body=[quality],type_ignores=[]),str(config_path),'exec'),cfg.__dict__)
cfg.QR=cfg.QualityRules()
path=SRC/'hydops/b2_quality/checks.py'
spec=importlib.util.spec_from_file_location('source_quality_checks',path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

rows=[]
for i,cid in enumerate([100,101,102]):
    for s in means:
        for sec in range(60):
            rows.append({'asset_id':'HYD-01','sensor_id':s,'origin_cycle_id':cid,'elapsed_s':sec,'ts':i*60+sec,'raw_value':means[s][cid][sec]})
checked=mod.SensorQualityChecker().check_many(rows)
control=dict(rows[0],raw_value=None)
control_result=mod.SensorQualityChecker().check(control)

normal=[i for i,p in enumerate(profile) if p[0]==100 and p[4]==0]
all_ids=list(range(len(profile)))
def max_change(s,ids):
    value,cid,sec=max((abs(means[s][i][j]-means[s][i][j-1]),i,j) for i in ids for j in range(1,60))
    return {'max_abs_delta':value,'cycle':cid,'elapsed_s':sec,'profile':profile[cid]}

result={
 'scope':'실제 원문 npz/profile와 원본 B2 검사 함수의 분리 실행. QualityRules는 원문 AST에서 로드. .env·DB·LLM·학생 전체 완주 없음.',
 'source_hashes':{str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [config_path,path,SRC/'data/raw/profile.txt',SRC/'data/reduced/hydraulic_1s.npz']},
 'source_profile_100_102':{str(i):profile[i] for i in (100,101,102)},
 'b2_flags':dict(Counter(r['quality_flag'] for r in checked)),
 'b2_by_cycle':{str(i):dict(Counter(r['quality_flag'] for r in checked if r['origin_cycle_id']==i)) for i in (100,101,102)},
 'quality_control_missing':control_result['quality_flag'],
 'normal_stable_selection':'cooler_pct == 100 and stable_flag == 0 (원문 B5 fixed_split과 동일 조건)',
 'normal_stable_count':len(normal),
 'max_change_all_2205':{s:max_change(s,all_ids) for s in means},
 'max_change_normal_stable':{s:max_change(s,normal) for s in means},
 'source_thresholds':cfg.QR.spike_delta,
 'interpretation':'OK와 냉각 이상 라벨은 서로 다른 평가 축이므로 동시 성립 가능. 정상 UCI라는 표현의 대상은 모호함. 전체2205개 최대를 정상 안정 구간 최대라고 설명하는 부분은 모집단 불일치.',
}
(OUT/'정상표현_근거확인.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))

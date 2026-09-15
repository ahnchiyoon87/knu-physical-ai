"""독립 소수 계산과 제공 함수 출력을 대조하고 실제 PS1 원본을 그린다."""
from decimal import Decimal
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import math

root, output = map(Path, sys.argv[1:3])
output.mkdir(parents=True, exist_ok=True)
target = output/'함수대조.json'
if target.exists():
    raise FileExistsError(target)

evidence = {}
for sid,hz in [('TS1',1),('FS1',10),('PS1',100)]:
    raw_path=root/f'플랫폼코드/data/raw/{sid}.txt'
    with raw_path.open(encoding='ascii') as stream:
        line=next(line for i,line in enumerate(stream) if i==100)
    values=[Decimal(v) for v in line.rstrip().split('\t')[:hz]]
    evidence[sid]={'cycle':100,'physical_line':101,'hz':hz,'relative_interval':'[0,1)',
                   'first':str(values[0]),'mean':str(sum(values)/hz),'min':str(min(values)),
                   'max':str(max(values)),'n':hz,'range':str(max(values)-min(values)),
                   'values':[str(v) for v in values],
                   'raw_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest()}
original_path=output/'원본.json'
if original_path.exists():
    assert json.loads(original_path.read_text(encoding='utf-8')) == evidence
else:
    original_path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')



def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, root/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sol = load('실습자료/1일차/완성본/practical/mapping.py', 'sol')
st = load('실습자료/1일차/원문시작본/practical/mapping.py', 'st')
records = []
for sid, data in evidence.items():
    raw = sol.read_raw_cycle(sid, 100)
    assert raw[:data['hz']].tolist() == [float(v) for v in data['values']]
    actual = sol.reduce_to_seconds(raw, data['hz'])[0]
    initial = st.reduce_to_seconds(raw, data['hz'])[0]
    for key in ['mean', 'min', 'max', 'n']:
        assert math.isclose(actual[key], float(data[key]), rel_tol=0, abs_tol=1e-10)
    assert initial['mean'] == float(data['first']) and initial['n'] == 1
    records.append({'sensor':sid,'provided_solution':actual,'provided_starter':initial,
                    'decimal_comparison_abs_tolerance':1e-10,'matches_independent_decimal':True})
first = Decimal(evidence['PS1']['first'])
assert Decimal(evidence['PS1']['mean'])-first == Decimal('22.9521')
# These are explicitly hypothetical, dimensionless sequences, not original measurements.
seqs = [[1,3,2,4],[4,2,3,1]]
stats = lambda xs: {'mean':sum(xs)/len(xs),'min':min(xs),'max':max(xs),'n':len(xs)}
assert seqs[0] != seqs[1] and stats(seqs[0]) == stats(seqs[1])
result = {'scope':'실제 원본 첫1초와 제공 함수의 통계 대조. 학생 완주 검증 아님.', 'records':records,
          'hypothetical_order_example':{'sequences':seqs,'statistics':stats(seqs[0]),'same_statistics_different_order':True}}
target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
font_manager.fontManager.addfont('/fonts/malgun.ttf')
plt.rcParams.update({'font.family':'Malgun Gothic','font.size':17,'axes.unicode_minus':False})
data=evidence['PS1'];values=[float(v) for v in data['values']]
fig,ax=plt.subplots(figsize=(14,7),dpi=140)
times=[i/data['hz'] for i in range(len(values))]
ax.plot(times,values,'o-',color='#2461ae',markersize=3.5,linewidth=1.5,label='원본100개 샘플')
ax.axhline(float(data['mean']),color='#bc6425',linewidth=2,linestyle='--',label='평균170.1621bar')
ax.scatter([0],[values[0]],s=115,color='#a8274d',zorder=5,label='첫 값147.21bar')
for key,label in [('min','최소141.27'),('max','최대189.88')]:
    value=float(data[key]);ax.axhline(value,color='#7e8997',linestyle=':',linewidth=1.2)
    ax.text(.99,value+1,label+'bar',ha='right',va='bottom',fontsize=15,color='#455569')
ax.set(xlim=(-.025,1.025),ylim=(132,200),xlabel='첫 샘플 기준 상대 시간(초)',ylabel='압력(bar)',title='PS1 · 사이클100 · 첫1초의 실제 원본')
ax.set_xticks([0,.2,.4,.6,.8,1]);ax.grid(alpha=.2);ax.legend(loc='upper left',fontsize=14)
fig.text(.5,.015,'PS1.txt 101번째 줄 · 인덱스0~99 · 100Hz · 선은 샘플을 연결한 표현',ha='center',fontsize=13,color='#53657b')
fig.tight_layout(rect=(0,.05,1,1))
fig.savefig(output/'압력_첫1초.png')
fig.savefig(output/'압력_첫1초.svg')
plt.close(fig)
print(json.dumps({'sensors_compared':len(records),'chart_points':len(values),'scope':'첫1초 실제 원본·함수·설명용 그래프'},ensure_ascii=False))

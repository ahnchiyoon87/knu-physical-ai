"""둘째 날 완성 코드의 실제 관측·DB 재조회 결과와 그래프를 저장한다."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import quality_lab as lab

OUTPUT=Path('/out')
OUTPUT.mkdir(parents=True,exist_ok=True)
rows=lab.make_injected_rows()
checked=lab.check_rows(rows)
run_id=lab.new_run_id()
try:
    inserted=lab.load_to_db(run_id,checked)
    fetched=lab.last_60s(run_id)
    assert inserted==180 and len(fetched)==60
    # DB에서 다시 읽은 값으로 그려 저장 성공과 관측의 대응을 보존한다.
    with (OUTPUT/'온도_품질조회.csv').open('w',encoding='utf-8-sig',newline='') as file:
        fields=['elapsed_s','raw_value','value','quality_flag','origin_cycle_id','unit']
        writer=csv.DictWriter(file,fieldnames=fields,extrasaction='ignore')
        writer.writeheader(); writer.writerows(fetched)
    (OUTPUT/'실행결과.json').write_text(json.dumps({
        'run_id':run_id,'inserted':inserted,'ts1_rows':len(fetched),
        'flags':{sid:lab.flag_counts(checked,sid) for sid in ['TS1','PS1','FS1']},
        'rows':checked,'database_rows':fetched},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    plt.rcParams['font.family']='NanumGothic'
    plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True,gridspec_kw={'height_ratios':[3,1]},layout='constrained')
    x=[r['elapsed_s'] for r in fetched]
    axes[0].plot(x,[r['raw_value'] for r in fetched],color='#8c8c8c',label='검사 전 값',linewidth=3)
    axes[0].plot(x,[r['value'] for r in fetched],color='#176eb1',label='판단에 사용할 값',linewidth=1.8)
    axes[0].set(ylabel='온도 [°C]',title='HYD-01 · TS1 · 사이클1500 오류 주입본의 DB 조회')
    axes[0].legend(); axes[0].grid(alpha=.2)
    categories=['OK','SPIKE','MISSING','GAP','STUCK']
    colors=['#237c43','#d25d1c','#888888','#a42525','#7540a0']
    for i,(category,color) in enumerate(zip(categories,colors)):
        points=[r['elapsed_s'] for r in fetched if r['quality_flag']==category]
        axes[1].scatter(points,[i]*len(points),label=category,color=color,s=25)
    axes[1].set(yticks=range(len(categories)),yticklabels=categories,xlabel='원본 사이클 안의 경과 초',xlim=(-1,60))
    axes[1].grid(axis='x',alpha=.2)
    fig.savefig(OUTPUT/'온도_품질조회.png',dpi=140)
    plt.close(fig)
    print(json.dumps({'inserted':inserted,'ts1_rows':len(fetched),'flags':{sid:lab.flag_counts(checked,sid) for sid in ['TS1','PS1','FS1']}},ensure_ascii=False))
finally:
    lab.cleanup(run_id)

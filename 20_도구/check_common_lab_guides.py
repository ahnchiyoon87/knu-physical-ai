"""Coverage and exact instructional prose checks, not a student rehearsal."""
import copy
import hashlib
import json
import re
from pathlib import Path
from lab_guide_content import UNITS
from common_lab_plan import FEATURES

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'intro','quality','visual','rules','pipeline','rag','eval','agent','transfer',
          'table','vision','rul','integration','deploy'}


def check_plan(records):
    for group,count in [('실전반',9),('통합반',10)]:
        rows=[r for r in records if r['group']==group]
        keys=[k for r in rows for k in r['keys']]
        if len(rows)!=count or set(keys)!=EXPECTED or len(keys)!=len(EXPECTED):
            raise ValueError('반별 필수 단위 또는 일차가 다릅니다')
        done=set()
        for r in rows:
            if set(r['start_features'])!=done:raise ValueError('이전 단계와 출발본 상태가 다릅니다')
            for key in r['keys']:done|=FEATURES[key]
            if set(r['complete_features'])!=done:raise ValueError('완성 상태와 오늘 기능이 다릅니다')


def main():
    data=json.loads((ROOT/'30_기록/공통실습가이드_매니페스트.json').read_text(encoding='utf-8'))
    records=data['records'];check_plan(records)
    for mutate in [lambda x:x[0]['keys'].clear(),lambda x:x[0]['start_features'].append('agent')]:
        bad=copy.deepcopy(records);mutate(bad)
        try:check_plan(bad)
        except ValueError:pass
        else:raise AssertionError('누락 또는 미래 기능 노출을 놓쳤습니다')
    schedule=json.loads((ROOT/'30_기록/일정원본.json').read_text(encoding='utf-8'))
    links=0;blocks=0
    for r in records:
        p=ROOT/r['guide'];text=p.read_text(encoding='utf-8')
        original=[x for x in schedule['offline'] if x['E'].startswith(r['group']) and x['I']!='OT/점검'][r['day']-1]
        assert (r['date'],r['time'])==(original['B'],original['F'])
        for key in r['keys']:
            for block in UNITS[key]['blocks']:
                for value in block:assert value in text,(r['guide'],key)
                blocks+=1
        for target in re.findall(r'\]\(([^)]+)\)',text):
            target=target.strip('<>')
            if target.startswith(('http:','https:')):continue
            assert (p.parent/target).exists(),target
            links+=1
    for name,h in data['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
    result={'guides':len(records),'units_each_cohort':14,'instruction_blocks':blocks,'local_links':links,
            'dates_times_preserved':True,'omission_and_future_state_fixture_rejected':True,
            'scope':'일정·필수 단위·본문 보존·로컬 링크·출발/완성 기능 계획. 실제 출발본 생성·실습 완주·수업시간 검증 아님'}
    (ROOT/'30_기록/공통실습가이드_검사.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()

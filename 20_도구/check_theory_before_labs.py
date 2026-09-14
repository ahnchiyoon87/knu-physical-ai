"""Verify current teaching-topic prerequisites against actual calendar dates."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED={'intro':'A','quality':'B','visual':'C','table':'F','rules':'D','pipeline':'EH',
          'vision':'G','rul':'I','integration':'EN','rag':'J','eval':'K','deploy':'L','agent':'OP','transfer':'OP'}


def assess(videos,labs,lookup):
    findings=[];checked=[]
    for lab in labs:
        for key in lab['keys']:
            for topic in REQUIRED[key]:
                choices=[v for v in videos if v['group']==lab['group'] and topic in {lookup[i] for i in v['slide_ids']}]
                if not choices:raise ValueError('실습에 필요한 이론 주제가 없습니다')
                video=min(choices,key=lambda v:v['release'])
                row={'group':lab['group'],'day':lab['day'],'lab':key,'topic':topic,'date':lab['date'],
                     'video':video['video'],'release':video['release'][:10]}
                checked.append(row)
                if row['release']>row['date']:findings.append(row)
    return checked,findings


def main():
    read=lambda name:json.loads((ROOT/'30_기록'/name).read_text(encoding='utf-8'))
    videos=read('영상별공통본_매니페스트.json')['records'];labs=read('공통실습가이드_매니페스트.json')['records']
    master=read('공통강의_매니페스트.json');lookup={s['id']:s.get('source_key') for u in master['units'] for s in u['slides']}
    checked,findings=assess(videos,labs,lookup)
    assert not findings,findings
    broken=copy.deepcopy(videos);broken[0]['release']='2099-12-31'
    assert assess(broken,labs,lookup)[1], '이론이 실습 뒤에 배포되는 사례를 놓쳤습니다'
    result={'checks':checked,'late_theory':findings,'late_release_fixture_rejected':True,
            'scope':'명시한 실습별 핵심 주제가 해당 반 실습일 이전 또는 당일 배포되는지 확인. 장별 모든 선수 개념·학습시간·학생 선행 시청을 보장하는 검사는 아님'}
    (ROOT/'30_기록/이론실습_선후검사.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'topic_date_checks':len(checked),'late_theory':len(findings)},ensure_ascii=False))


if __name__=='__main__':main()

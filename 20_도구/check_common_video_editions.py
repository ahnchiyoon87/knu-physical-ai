"""Check that both calendars cover identical canonical slides, in order."""
import copy
import hashlib
import json
from build_common_course import ROOT,render


def coverage(records,ids):
    for group,n in [('실전반',8),('통합반',11)]:
        rows=[r for r in records if r['group']==group]
        if len(rows)!=n or [s for r in rows for s in r['slide_ids']]!=ids:
            raise ValueError('반별 공통 장면의 누락·중복·순서 차이')


def main():
    master=json.loads((ROOT/'30_기록/공통강의_매니페스트.json').read_text(encoding='utf-8'))
    data=json.loads((ROOT/'30_기록/영상별공통본_매니페스트.json').read_text(encoding='utf-8'))
    schedule=json.loads((ROOT/'30_기록/일정원본.json').read_text(encoding='utf-8'))['videos']
    ids=[s['id'] for u in master['units'] for s in u['slides']]
    coverage(data['records'],ids)
    bad=copy.deepcopy(data['records']);bad[0]['slide_ids'].pop()
    try:coverage(bad,ids)
    except ValueError:pass
    else:raise AssertionError('장면 누락을 놓쳤습니다')
    for name,h in data['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
    for r in data['records']:
        original=next(x for x in schedule if x['D']==r['group'] and x['E']==f'영상{r["video"]}')
        assert (r['release'],r['deadline'],r['required_hours'])==(original['C'],original['B'],int(original['H']))
        u=master['units'][r['common_unit']-1];lookup={s['id']:s for s in u['slides']};slides=[lookup[i] for i in r['slide_ids']]
        full=(ROOT/r['deck']).read_text(encoding='utf-8');spoken=(ROOT/r['script']).read_text(encoding='utf-8')
        assert render(r['title'],slides) in full
        assert render(r['title'],slides,True) in spoken
        for i,path in enumerate(r['parts']):assert render(r['title'],slides[i*12:(i+1)*12]) in (ROOT/path).read_text(encoding='utf-8')
    result={'videos':len(data['records']),'same_slides_each_cohort':len(ids),'files':len(data['files']),
            'dates_hours_preserved':True,'missing_slide_fixture_rejected':True,
            'scope':'두 반 전체 장면 순서·본문·대본·분할·원본 배포/마감/시수 일치. 실제 녹화 길이와 실습 선후 관계 충족 검증 아님'}
    (ROOT/'30_기록/영상별공통본_검사.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()

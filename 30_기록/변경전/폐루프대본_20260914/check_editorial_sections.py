"""Verify the exact edited slide/script ranges and preserve evidence of unaffected decks."""
import hashlib
import json
from pathlib import Path
from build_decks import ROOT,render
from deck_content import CAT
from narration_application import APPLICATION
from narration_case_review import CASE_NARRATION


def require_fragment(text,fragment):
    if fragment not in text:raise ValueError('작성한 문구가 출력에 없습니다')


def main():
    require_fragment('정상 근거 문장','근거')
    try:require_fragment('누락된 입력','근거')
    except ValueError:pass
    else:raise AssertionError('누락 검사를 확인하지 못했습니다')
    decks=json.loads((ROOT/'30_기록/덱_매니페스트.json').read_text(encoding='utf-8'))
    narrations=json.loads((ROOT/'30_기록/대본_매니페스트.json').read_text(encoding='utf-8'))['written']
    changed=json.loads((ROOT/'30_기록/적용장면_변경기록.json').read_text(encoding='utf-8'))
    before=json.loads((ROOT/changed['backup']/'덱_매니페스트.json').read_text(encoding='utf-8'))
    rows=[];untouched=0
    for deck in decks:
        old=next(r for r in before if r['path']==deck['path'])
        if deck['key'] not in changed['keys']:
            assert old['sha256']==deck['sha256']==hashlib.sha256((ROOT/deck['path']).read_bytes()).hexdigest()
            untouched+=1;continue
        key=deck['key'];meta=deck['meta'];start=2+len(CAT[key])*3
        text=(ROOT/deck['path']).read_text(encoding='utf-8')
        assert text==render(meta,key,deck['slides'])
        for i,detail in enumerate(APPLICATION[key]):
            assert detail['anchor'] in deck['slides'][start+i]['screen']
            require_fragment(text,detail['anchor'])
        script=next(n for n in narrations if n['group']==meta['반'] and n['video']==meta['영상'])
        spoken=(ROOT/script['path']).read_text(encoding='utf-8')
        for detail in APPLICATION[key]:require_fragment(spoken,detail['spoken'])
        for pair in CASE_NARRATION.get(key,[]):
            for paragraph in pair:require_fragment(spoken,paragraph)
        for number,name in enumerate(deck['parts']):
            ids=[s['id'] for s in deck['slides'][number*12:(number+1)*12]]
            assert (ROOT/name).read_text(encoding='utf-8')==render(meta,key,deck['slides'],ids)
        rows.append({'deck':deck['path'],'script':script['path'],'screen_edits':18,
            'application_narrations':18,'case_narrations':2*len(CASE_NARRATION.get(key,[])),
            'spoken_characters':script['spoken_characters']})
    report={'results':rows,'unaffected_decks_verified':untouched,'checker_valid_and_invalid_verified':True,
        'scope':'J/K 적용 장면·사례의 집필 소스가 전체·분할 덱·대본에 반영됐는지 확인. 녹화 길이와 전체 강의 완료의 증거 아님'}
    (ROOT/'30_기록/적용대본_대조검사.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()

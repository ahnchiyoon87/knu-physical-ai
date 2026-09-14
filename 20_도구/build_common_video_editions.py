"""Package the identical shared slide sequence into the original 8/11 video slots."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from build_common_course import ROOT, render

OUT=ROOT/'00_문서/영상별공통본'
MANIFEST=ROOT/'30_기록/영상별공통본_매니페스트.json'


def partition(unit,key):
    cut=next(i for i,s in enumerate(unit['slides']) if s.get('transition_to')==key)
    return unit['slides'][:cut],unit['slides'][cut:]


def main():
    shared=json.loads((ROOT/'30_기록/공통강의_매니페스트.json').read_text(encoding='utf-8'))
    for name,h in shared['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise ValueError('공통 원고 변경을 먼저 확인하세요: '+name)
    old=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {'files':{}}
    for name,h in old['files'].items():
        if not (ROOT/name).exists() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise ValueError('영상별 원고 편집을 보호합니다: '+name)
    units=shared['units'];schedule=json.loads((ROOT/'30_기록/일정원본.json').read_text(encoding='utf-8'))['videos']
    practical=[(u,u['title'],u['slides']) for u in units]
    integrated=[]
    splits={5:('I','이미지 이상 판별','남은 수명과 기준 도달'),7:('L','근거 인용과 응답 평가','서비스 배포와 영속 상태'),8:('P','에이전트와 도구 사용','승인과 재관측의 폐루프')}
    for u in units:
        if u['unit'] in splits:
            key,a,b=splits[u['unit']];left,right=partition(u,key)
            integrated.extend([(u,a,left),(u,b,right)])
        else:integrated.append((u,u['title'],u['slides']))
    planned={};records=[]
    for group,editions in [('실전반',practical),('통합반',integrated)]:
        for n,(unit,title,slides) in enumerate(editions,1):
            original=next(r for r in schedule if r['D']==group and r['E']==f'영상{n}')
            folder=OUT/group/f'영상{n:02d}'
            head=(f'# {group} 영상{n} · {title}\n\n제작 마감: {original["B"]} · 배포일: {original["C"]} · 원본 영상 시수: {original["H"]}H\n\n'
                  '아래 원고는 두 반이 사용하는 같은 공통 내용의 영상별 묶음입니다. 공통 장 번호를 유지합니다. 시수는 일정의 요구값이며 현재 낭독 분량을 측정해 충족을 확인한 값이 아닙니다.\n\n')
            full=(ROOT/unit['deck']).read_text(encoding='utf-8')
            footer=full[len(render(unit['title'],unit['slides'])):]
            deck=folder/'이론덱.md';script=folder/'온라인대본.md'
            planned[deck]=head+render(title,slides)+footer
            planned[script]=head+render(title,slides,True)
            parts=[]
            for start in range(0,len(slides),12):
                path=folder/'NotebookLM_분할'/f'{start//12+1:02d}.md'
                planned[path]=head+render(title,slides[start:start+12])+footer;parts.append(path.relative_to(ROOT).as_posix())
            records.append({'group':group,'video':n,'title':title,'common_unit':unit['unit'],
                            'slide_ids':[s['id'] for s in slides],'spoken_characters':sum(len(s['spoken']) for s in slides),
                            'deadline':original['B'],'release':original['C'],'required_hours':int(original['H']),
                            'source_excel_row':original['row'],'source_title':original['G'],
                            'deck':deck.relative_to(ROOT).as_posix(),'script':script.relative_to(ROOT).as_posix(),'parts':parts})
    lines=['# 공통 내용의 영상별 제작본','',
           '실전반 8편과 통합반 11편은 동일한 공통 장면을 같은 순서로 사용합니다. 통합반은 이미지/수명, 평가/배포, 도구/폐루프를 각각 나눕니다. 양쪽 모두 빠짐없이 같은 내용을 다루며 공통 장 번호를 유지합니다.','',
           '현재는 집필본입니다. 원본 영상 시수 32H/44H를 그대로 기록했지만 낭독 분량과 수업시간 충족은 아직 검토 중입니다. 추가 설명을 작성할 때도 한쪽에만 필수 주제를 두지 않고 공통 원고에 반영합니다.','',
           '| 반 | 영상 | 배포일 | 제목·덱 | 온라인 대본 | 장수 |','|---|---|---|---|---|---:|']
    for r in records:
        base=f'{r["group"]}/영상{r["video"]:02d}'
        lines.append(f'| {r["group"]} | {r["video"]} | {r["release"]} | [{r["title"]}](<{base}/이론덱.md>) | [대본](<{base}/온라인대본.md>) | {len(r["slide_ids"])} |')
    lines+=['','원자료의 영상 제목은 매니페스트에 보존했습니다. 최신 공통 내용 지시에 맞춰 제목과 묶음을 변경했습니다. 공통 실습 가이드는 이론을 먼저 보지 않았어도 따라갈 수 있게 해당 설명을 포함하며, 영상 배포일과 실습 단위의 세부 선후 관계 검토는 별도로 진행합니다.','']
    planned[OUT/'README.md']='\n'.join(lines)
    for path in planned:
        if path.exists() and path.relative_to(ROOT).as_posix() not in old['files']:raise ValueError('관리하지 않는 파일을 덮지 않습니다')
    changed=[p for p,text in planned.items() if p.exists() and p.read_text(encoding='utf-8')!=text]
    if changed:
        backup=ROOT/'30_기록/변경전'/('영상별공통본_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
        for p in changed:
            dest=backup/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        shutil.copy2(MANIFEST,backup/MANIFEST.name)
    for p,text in planned.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
    MANIFEST.write_text(json.dumps({'records':records,'files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in planned},
                                    'status':'공통 내용의 영상별 집필본; 시간 충족 미검증'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'videos':len(records),'files':len(planned),'shared_slides_each':sum(len(u['slides']) for u in units)},ensure_ascii=False))


if __name__=='__main__':main()

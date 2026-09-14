"""Build full linear daily guides from common authored content; no lab execution."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from lab_guide_content import UNITS
from lab_intro_guidance import AFTER_ACTION
from lab_quality_guidance import QUALITY_ACTION
from lab_table_guidance import TABLE_ACTION
AFTER_ACTION = {**AFTER_ACTION, **QUALITY_ACTION, **TABLE_ACTION}
from common_lab_plan import ORDER, THEORY, stages

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'10_실습/공통학생가이드'
MANIFEST=ROOT/'30_기록/공통실습가이드_매니페스트.json'
QUESTIONS=['실제 사출 압력이 가장 높은 샷 10개는?','배럴 온도 네 구간 평균은?',
 'LOT별 쿠션 평균은?','평균 쿠션이 가장 낮은 LOT는?','계량시간 평균은?',
 '데이터 마지막 LOT 기준 최근 다섯 LOT의 사이클 평균은?','배압의 최댓값은?',
 '불량이 많은 LOT는?','조건표의 기준과 다른 LOT는?','쿠션이 8 mm 미만인 샷은 몇 개인가?']
EXTRA = {
 ('rules',0): '참고 구현의 세 규칙은 LOT 조건표 기준 ±1.5 mm, LOT 첫 200행 평균 대비 2.5% 초과 변화, 쿠션 2.5% 초과 상승 AND 계량시간 2.5% 초과 하락입니다. 교육용 기준입니다. 조건표의 적용 행이 하나인지 확인하고 첫 200행 뒤의 관측을 판정합니다.',
 ('agent',1): '합성 관계표의 LOT → 작업일지 → `synthetic:document:FOURM` → `synthetic:document:FIRST`는 조사할 절차를 연결한 교육용 설계입니다. 실제 조건 변경의 증거는 아닙니다. 관계표를 적재한 뒤 끝 대상 ID를 입력합니다.',
}
PREDICT='예측을 같은 실행에 묶으려면 `forecast.json`에 선택 LOT·열 번호·horizon을 넣도록 요청합니다. `uv run --env-file .env python scripts/reload.py --profile synthetic --source shots --rule cushion-relative --predict forecast --parameters forecast.json`으로 연결할 수 있습니다. 예측을 요청하지 않은 상태와 요청한 예측의 실패를 구별합니다.'
for key in ('pipeline','integration'):EXTRA[(key,3)]=PREDICT


def main():
    old=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {'files':{}}
    for name,h in old['files'].items():
        if not (ROOT/name).exists() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:
            raise ValueError('현재 공통 가이드 편집을 보호합니다: '+name)
    schedule=json.loads((ROOT/'30_기록/일정원본.json').read_text(encoding='utf-8'))
    common=json.loads((ROOT/'30_기록/공통강의_매니페스트.json').read_text(encoding='utf-8'))
    planned={};records=[]
    for record in stages():
        group=record['group'];day=record['day'];keys=record['keys']
        rows=[r for r in schedule['offline'] if r['E'].startswith(group) and r['I']!='OT/점검']
        assert len(rows)==len(ORDER[group])
        row=rows[day-1];folder=OUT/group;path=folder/f'{day:02d}일차.md'
        title=' · '.join(UNITS[k]['title'] for k in keys)
        lines=[f'# {group} {day}일차 · {title}','',f'일정: {row["B"]} {row["F"]} · 4시간','',
               '## 오늘 작업을 엽니다 · 20분','',
               '잘 이어지는 자기 프로젝트는 그대로 사용합니다. 결석했거나 진행이 막혔다면 오늘 배포받은 출발본을 새 폴더에서 엽니다. 자기 작업을 삭제하거나 덮지 않습니다. 두 폴더의 서버를 동시에 실행하지 않습니다.','',
               ('첫날 출발본에는 앱 코드가 없습니다. VS Code에서 `constitution.md`와 `mapping.json`이 보이는 프로젝트 폴더를 열고 아래 첫 행동부터 시작합니다. 서버 실행은 첫 화면을 만든 뒤에 진행합니다.' if day==1 else 'VS Code에서 작업 폴더를 열고 README와 실행 연결 안내 순서로 이전 단계의 서버와 자료 연결을 확인합니다. 오늘 기능은 그 위에 코딩 에이전트에게 목적과 확인 기준을 설명하며 만듭니다.'),'',
               '설치가 남았다면 [Google Cloud](../../../실습가이드핸즈온문서/1_GoogleCloud세팅.pdf), [VS Code와 코딩 에이전트](../../../실습가이드핸즈온문서/2_VSCode설치및_코딩에이전트세팅.pdf), [Docker](../../../실습가이드핸즈온문서/3_도커설치및세팅.pdf), [의존성](../../../실습가이드핸즈온문서/4_실습의존성설치.pdf) 중 필요한 단계를 마칩니다. 설치 뒤에는 [실행 연결 안내](../../학생가이드/실행_연결_안내.md)를 확인합니다.','',
               'synthetic은 교육용 합성, kamp는 직접 연결한 원본입니다. 원본 경로가 없으면 자료를 준비해야 합니다. 합성을 사용했다면 결과에도 표시합니다. 모델 호출 전 사용할 계정과 모델, 예상 비용을 확인하고 허용하지 않은 실행은 시작하지 않습니다.','']
        theory=sorted({n for k in keys for n in THEORY[k]})
        links=[]
        for n in theory:
            u=common['units'][n-1];target='../../../'+u['deck']
            links.append(f'[{n}. {u["title"]}](<{target}>)')
        lines+=['연결 이론: '+' · '.join(links)+'. 아래 행동에 필요한 설명은 이 문서에도 있으므로 이론을 보지 않았어도 현재 단계부터 읽습니다.','']
        block_count=sum(len(UNITS[k]['blocks']) for k in keys)
        minutes=200//block_count;step=0
        for key in keys:
            unit=UNITS[key]
            lines += [f'## {unit["title"]}','',f'만들 결과: **{unit["result"]}**','',unit['arrival'],'']
            for i,(heading,why,action,check,recovery,bridge) in enumerate(unit['blocks']):
                step+=1
                if key=='intro' and i==1:
                    lines+=['### 지금 비교할 질문','', '질문에 조건이 부족할 수도 있습니다. 답을 만들기 전에 어떤 근거가 필요한지도 판단합니다.','']
                    lines += [f'{j}. {q}' for j,q in enumerate(QUESTIONS,1)]
                    lines += ['', '맞음·틀림·근거 없이 지어냄·실패/조건 부족을 구분하며 같은 질문으로 첫 버전과 변경한 버전을 비교합니다.','']
                if key in ('rag','eval') and i==0:
                    lines+=['[RAG 질문 20개](../../학생가이드/자료/RAG_질문20.json)와 [내 질문 작성틀](../../학생가이드/자료/내_질문30_작성틀.json)을 준비합니다. 빈 질문으로 평가하지 않고 자기 질문과 기대 근거를 넣습니다.','']
                if (key,i) in EXTRA:lines += [EXTRA[(key,i)],'']
                lines += [f'### {step}. {heading} · 약 {minutes}분','',why,'',action,'']
                if (key,i) in AFTER_ACTION:lines += [AFTER_ACTION[(key,i)],'']
                lines += ['**결과를 읽습니다.** '+check,'','**막히면 여기서 확인합니다.** '+recovery,'',bridge,'']
        lines+=['## 오늘 만든 것을 이어갈 준비 · 20분','',
                '현재 폴더와 실행 설정을 저장하고 오늘 확인한 대표 입력을 다시 찾을 수 있게 둡니다. 아직 실행하지 않은 모델이나 부족한 자료는 성공 결과로 바꾸지 않습니다. 다음 시간에는 자기 프로젝트를 이어가거나 그날 출발본으로 합류할 수 있습니다.','',
                '참고 완성본과 화면이나 코드가 같을 필요는 없습니다. 원하는 입력과 결과가 연결되고, 근거와 한계를 설명할 수 있는지 확인합니다. 별도 회고문 제출이나 정해진 모양의 개인 노트는 요구하지 않습니다.','']
        planned[path]='\n'.join(lines)
        record.update(date=row['B'],time=row['F'],original_title=row['J'],guide=path.relative_to(ROOT).as_posix(),
                      block_count=block_count,estimated_work_minutes=minutes*block_count,estimated_total_minutes=40+minutes*block_count)
        records.append(record)
    index=['# 두 반 공통 내용의 일차별 실습가이드','',
           '두 반은 같은 14개 실습 단위를 진행합니다. 실제 날짜에 맞춰 묶음만 다릅니다. 시간은 수업 설계용 추정이며 학생 완주로 측정한 값이 아닙니다. [수업 시작 ZIP](../공통배포/README.md)과 [출발본·완성본 코드](../공통코드/README.md)를 구분해 사용합니다. 기존 반별 패키지를 이 순서의 출발본으로 혼용하지 않습니다.','',
           '| 반 | 일차 | 일정 | 실습 단위 |','|---|---|---|---|']
    for r in records:index.append(f'| {r["group"]} | [{r["day"]}일차]({r["group"]}/{r["day"]:02d}일차.md) | {r["date"]} {r["time"]} | {", ".join(r["keys"])} |')
    planned[OUT/'README.md']='\n'.join(index)+'\n'
    for path in planned:
        if path.exists() and path.relative_to(ROOT).as_posix() not in old['files']:
            raise ValueError('기존 비관리 파일을 보호합니다: '+str(path))
    changed=[p for p,text in planned.items() if p.exists() and p.read_text(encoding='utf-8')!=text]
    if changed:
        backup=ROOT/'30_기록/변경전'/('공통가이드_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
        for p in changed:
            dest=backup/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
        shutil.copy2(MANIFEST,backup/MANIFEST.name)
    for p,text in planned.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
    data={'records':records,'status':'공통 일차별 가이드 집필본; 공통 코드·수업 시작 ZIP 생성, 전체 의미·시간 검토 중',
          'files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in planned}}
    MANIFEST.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'guides':len(records),'units_per_cohort':14,'files':len(planned)},ensure_ascii=False))


if __name__=='__main__':main()

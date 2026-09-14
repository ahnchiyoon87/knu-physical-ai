"""Assemble schedule-specific, linear guides from authored unit prose."""
import hashlib
import json
from pathlib import Path

from lab_guide_content import UNITS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'10_실습/학생가이드'
APP=ROOT/'10_실습/완성본/equipment-assistant'
SCHEDULE=json.loads((ROOT/'30_기록/일정원본.json').read_text(encoding='utf-8'))
ORDER={'실전반':['intro','quality','visual','rules','pipeline','rag','eval','agent','transfer'],
       '통합반':['intro','table','vision','pipeline','rul','integration','rag','eval','deploy','agent']}
HINTS={'intro':3,'quality':3,'visual':2,'rules':2,'pipeline':2,'table':2,'vision':2,'rul':2,'integration':2,'rag':1,'eval':1,'deploy':1,'agent':1,'transfer':0}
SUPPORT={
 'intro':['열의 뜻과 단위는 mapping.json에서 확인합니다.','모델의 답 옆에 실제 SQL과 결과표가 있어야 비교할 수 있습니다.','관계는 양쪽 대상 ID와 근거가 맞는 한 줄부터 시작합니다.'],
 'quality':['0·결측·오류 코드가 같은 뜻인지부터 확인합니다.','전체 기준과 LOT별 기준의 분모를 나눕니다.','뜻 초안의 인용을 실제 원문에서 찾아봅니다.'],
 'visual':['먼저 어떤 범위·단위를 보면 됐다고 할지 정합니다.','숫자 계산과 문장 생성을 나눠 봅니다.'],
 'rules':['전체 기준인지 그 LOT의 기준인지 먼저 정합니다.','걸린 행 수와 사람에게 보낸 통지 수는 별개입니다.'],
 'pipeline':['처음 실패한 단계는 어디인가요?','비교 방법들의 입력 구간이 같은가요?'],
 'table':['정답을 드러내는 열이 입력에 들어 있나요?','놓친 불량의 분모는 전체입니까, 평가 구간입니까?'],
 'vision':['온도 표현과 좌우 구분이 모든 샘플에서 같나요?','기준을 고른 자료와 마지막 평가 자료가 섞였나요?'],
 'rul':['정답 고장 시점이 실제로 있나요?','비교하는 두 예측의 목표 구간이 같은가요?'],
 'integration':['완료를 증명할 결과를 할 일마다 정합니다.','한 단계의 빈 입력이 다음에 어떻게 전달되는지 봅니다.'],
 'rag':['틀린 답들은 같은 이유로 틀렸나요?'], 'eval':['점수 변화가 실제로 같은 질문·근거 범위에서 나왔나요?'],
 'deploy':['재시작 뒤 반드시 남아야 할 것은 무엇인가요?'], 'agent':['사람이 승인한 대상과 실제 기록한 대상이 같은가요?'],'transfer':[]}


def write(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(content.rstrip()+'\n',encoding='utf-8')


def main():
    manifest=ROOT/'30_기록/실습가이드_매니페스트.json'
    if manifest.exists():
        for item in json.loads(manifest.read_text(encoding='utf-8')):
            path=ROOT/item['guide']
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=item['hash']:
                raise ValueError('가이드의 사용자 편집을 보호합니다: '+str(path))
    records=[]
    index=['# 일차별 실습가이드','', '매일 자신의 프로젝트로 이어 갑니다. 결석했거나 이어가기 어려우면 같은 일차의 출발본을 새 폴더에서 엽니다. 가이드는 오늘 필요한 개념과 행동을 함께 설명합니다. 화면 결과는 참고 완성본과 똑같을 필요가 없습니다.','',
        '| 반 | 일차 | 일정 | 오늘 만들 것 |','|---|---|---|---|']
    for group,keys in ORDER.items():
        rows=[r for r in SCHEDULE['offline'] if r['E'].startswith(group) and r['I']!='OT/점검']
        assert len(rows)==len(keys)
        for number,(row,key) in enumerate(zip(rows,keys),1):
            unit=UNITS[key]
            identity=f'{group}_{number:02d}일차'
            path=OUT/group/f'{number:02d}일차_{key}.md'
            prefix='실' if group=='실전반' else '통'
            starter=f'{prefix}{number:02d}-start'
            script_path='../../../00_문서/이론덱'
            lines=[f'# {group} {number}일차 · {unit["title"]}','',
                f'일정: {row["B"]}({row["C"]}) {row["F"]} · 4시간',
                f'연결 이론: {row.get("K","새 영상 없음 · 앞선 내용 적용")} · [이론 덱 목록]({script_path}/README.md)','',
                f'오늘 만들 것: **{unit["result"]}**','',
                '## 0:00–0:20 · 오늘 작업을 엽니다','',unit['arrival'],'',
                f'ESNS에서 오늘 공개된 Drive 링크의 **{starter}**와 이 가이드를 받습니다. 잘 이어지는 자기 프로젝트가 있으면 그것을 씁니다. 출발본은 이전 단계의 코드이므로 오늘 기능은 직접 요청해 만듭니다. 내 작업이 막혔다면 기존 폴더는 보존하고 출발본을 새 폴더에 풉니다. 두 폴더에 같은 서버를 동시에 띄우지 않습니다.','',
                'VS Code에서 오늘 작업 폴더를 열고 README의 실행 순서를 확인합니다. 이미 만든 서비스는 연결 확인에서 서버·DB 상태를 읽고, 오늘 필요한 원천 파일과 모델 준비 여부를 따로 확인합니다. 첫날 코드 없는 뼈대에서는 아직 앱 화면이 없는 것이 맞습니다. 설치가 남았다면 아래 네 문서 중 해당 단계만 마칩니다.','',
                '- [Google Cloud 세팅](../../../실습가이드핸즈온문서/1_GoogleCloud세팅.pdf)',
                '- [VS Code와 코딩 에이전트](../../../실습가이드핸즈온문서/2_VSCode설치및_코딩에이전트세팅.pdf)',
                '- [Docker 설치](../../../실습가이드핸즈온문서/3_도커설치및세팅.pdf)',
                '- [실습 의존성 설치](../../../실습가이드핸즈온문서/4_실습의존성설치.pdf)','',
                '설치 뒤의 서버·자료 연결은 [실행 연결 안내](../실행_연결_안내.md)에 모았습니다. 이 문서는 설치 프로그램 설명을 반복하지 않고 실제 프로젝트의 실행과 오류 위치를 이어 줍니다.','',
                '자료를 선택할 때 synthetic은 교육용 합성, kamp는 직접 연결한 KAMP 원본입니다. 원본을 선택했는데 파일이 없으면 원본 경로를 먼저 준비합니다. 합성을 썼다면 결과에도 합성이라고 표시합니다. 특정 LOT의 실제 숫자가 가이드와 같아야 통과하는 수업은 아닙니다.','']
            for block,(title,why,action,check,recovery,bridge) in enumerate(unit['blocks'],1):
                start=20+(block-1)*50; end=start+50
                timing=lambda m:f'{m//60}:{m%60:02d}'
                lines += [f'## {timing(start)}–{timing(end)} · {title}','',why,'',
                    '**지금 해 볼 일**','',action,'',
                    '에이전트에게 줄 요청은 자신의 말로 씁니다. 원하는 행동과 무엇을 보면 됐다고 할지를 전달하고, 나온 이해가 다르면 바로잡습니다. 구현 문법을 직접 완성할 필요는 없습니다.','',
                    '**됐는지 확인합니다**','',check,'',
                    '**막혔을 때**','',recovery,'',bridge,'']
            if HINTS[key]:
                lines+=['## 필요한 만큼만 보는 오늘의 힌트','']+['- '+x for x in SUPPORT[key]]+['']
            lines += ['## 3:40–4:00 · 오늘 결과를 설명합니다','',
                '직접 실행한 한 동선을 골라 입력→처리→결과→근거를 짧게 설명합니다. 원하는 기능을 어떻게 요청했는지, 결과를 무엇으로 확인했는지, 다음 기능과 어떻게 연결했는지, 어디까지 말할 수 있는지가 보이면 됩니다. 다른 학생과 화면이나 답 문장이 같을 필요는 없습니다.','',
                '오늘 작업을 저장합니다. 다음에 열 경로와 마지막으로 되는 동작을 README에 남기면 이어가기 쉽습니다. 개인 비교 노트나 추가 제출 형식을 따로 요구하지 않습니다. 완성본은 본인 작업과 비교할 때 사용하고, 다음 일차에는 다음 출발본으로 다시 합류할 수 있습니다.','',
                '모델 호출·학습·배포를 실제로 하지 않은 항목은 미실행으로 표시합니다. 문법 검사나 화면 빌드가 됐다는 이유로 실습 전체를 완료했다고 적지 않습니다.','',
                '### 오늘 확인하는 네 가지','',
                '| 시키기 | 확인하기 | 이어 붙이기 | 한계 알기 |','|---|---|---|---|',
                '| 내 목적과 확인 기준이 요청에 있다 | 입력·범위·근거로 결과를 대조한다 | 오늘 기능이 기존 자료·화면과 이어진다 | 없는 자료·미확인 결과를 구분한다 |','']
            if key=='intro':
                before_questions=len(lines)
                lines+=['### 첫날 질문 10개','',
                    '아래 질문을 그대로 답안처럼 외우지 않고 하나씩 자신의 말로 묻습니다. 어느 질문에 조건이 부족한지도 판단합니다. 샷·조건표·작업일지를 함께 쓰는 질문은 관련 원천을 모두 선택해야 합니다.','']
                for i,text in enumerate(['실제 사출 압력이 가장 높은 샷 10개는?','배럴 온도 네 구간 평균은?','LOT별 쿠션 평균은?','평균 쿠션이 가장 낮은 LOT는?','계량시간 평균은?','데이터 마지막 LOT 기준 최근 다섯 LOT의 사이클 평균은?','배압의 최댓값은?','불량이 많은 LOT는?','조건표의 기준과 다른 LOT는?','쿠션이 8 mm 미만인 샷은 몇 개인가?'],1):
                    lines.append(f'{i}. {text}')
                lines+=['','답을 평가할 때 **맞음 / 틀림 / 근거 없이 지어냄 / 답변 실패·조건 부족**을 구분합니다. 열 사전 없이 만든 첫 버전과 사전·정찰·관계를 하나씩 추가한 버전을 같은 질문으로 비교합니다. 번호 출력은 존재하지 않는 열을 코드가 거절하기 쉽게 만들 뿐 의미를 맞힌다는 보장은 아닙니다.','']
                questions=lines[before_questions:];lines=lines[:before_questions]
                at=next(i for i,line in enumerate(lines) if line.startswith('## 1:10–'))
                lines[at:at]=questions
            if key in {'rag','eval'}:
                at=next(i for i,line in enumerate(lines) if line.startswith('## 0:20–'))
                lines[at:at]=['오늘 사용할 [RAG 질문 20개](../자료/RAG_질문20.json)와 [내 질문 30개 작성틀](../자료/내_질문30_작성틀.json)을 작업 폴더에 받습니다. 작성틀은 빈 질문이므로 실제 자기 질문과 기대 근거를 채운 뒤 평가합니다.','']
            if key=='rules':
                at=next(i for i,line in enumerate(lines) if line.startswith('## 0:20–'))
                lines[at:at]=['참고 구현의 세 규칙은 LOT 조건표 기준 ±1.5 mm, LOT 첫 200행 평균 대비 2.5% 초과 변화, 쿠션 2.5% 초과 상승 AND 계량시간 2.5% 초과 하락입니다. 수치는 교육용 설계이며 실제 공정 기준이 아닙니다. 조건표를 먼저 적재하고 현재 LOT의 적용 행이 하나인지 확인합니다. 첫 200행은 자기 대비 기준에만 쓰며 뒤 관측을 판정합니다.','']
            if key=='quality':
                at=next(i for i,line in enumerate(lines) if line.startswith('## 2:50–'))
                lines[at:at]=['정제 뷰를 실제 분석에 쓰기로 했다면 코딩 에이전트에게 mapping.json의 해당 원천에 `analysis_view: "clean"`을 지정하도록 요청합니다. 정제 뷰를 먼저 만든 뒤 서버를 다시 시작하면 질문·곡선·감지가 같은 정제 뷰를 읽습니다. `raw`는 원본 뷰입니다. 정제 뷰가 없으면 오류를 반환하며 원본으로 조용히 대신하지 않습니다.','']
            if key=='agent':
                at=next(i for i,line in enumerate(lines) if line.startswith('## 1:10–'))
                lines[at:at]=['합성 관계표에서는 선택 LOT → 작업일지 → `synthetic:document:FOURM` → `synthetic:document:FIRST`를 따라갈 수 있습니다. 이는 조사할 절차를 연결한 교육용 설계이며 해당 LOT에 실제 조건 변경이 있었다는 증거가 아닙니다. 관계표를 그래프에 적재한 뒤 끝 대상 ID를 입력하고, 문서의 적용 의미를 대조합니다.','']
            if key in {'pipeline','integration'}:
                at=next(i for i,line in enumerate(lines) if line.startswith('## 2:50–'))
                lines[at:at]=['예측을 같은 실행에 묶을 때는 원하는 분석 설정을 JSON 파일로 저장하도록 에이전트에게 요청합니다. 예를 들어 `forecast.json`에 선택 LOT·열 번호·horizon을 넣고 `uv run --env-file .env python scripts/reload.py --profile synthetic --source shots --rule cushion-relative --predict forecast --parameters forecast.json`을 실행합니다. `--predict`를 빼면 예측을 요청하지 않은 실행이며, 요청한 예측이 실패하면 감지 완료와 예측 부족을 나눠 반환해야 합니다.','']
            write(path,'\n'.join(lines))
            records.append({'id':identity,'group':group,'day':number,'key':key,'starter':starter,'date':row['B'],'time':row['F'],
                'guide':str(path.relative_to(ROOT)).replace('\\','/'),'hash':hashlib.sha256(path.read_bytes()).hexdigest()})
            index.append(f'| {group} | [{number}일차]({group}/{path.name}) | {row["B"]} {row["F"]} | {unit["result"]} |')
    index += ['','[합동 OT](합동_OT.md) · [실행 연결 안내](실행_연결_안내.md)','',
        '학습 순서의 기준은 원자료 ZIP·실습 흐름과 실제 일정입니다. 개인 노트 의무·부정행위 통제·자동 유료 실행은 최신 사용자 지시에 따라 넣지 않았습니다.']
    write(OUT/'README.md','\n'.join(index))
    write(ROOT/'30_기록/실습가이드_매니페스트.json',json.dumps(records,ensure_ascii=False,indent=2))
    print(json.dumps({'guides':len(records),'groups':{k:len(v) for k,v in ORDER.items()}},ensure_ascii=False))


if __name__=='__main__':main()

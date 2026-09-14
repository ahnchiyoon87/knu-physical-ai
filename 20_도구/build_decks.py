"""집필 원고를 일정별 Markdown으로 조립한다. 모델·실습·외부 서비스 실행 없음."""
from pathlib import Path
import json,re,hashlib
from deck_content import CAT
from deck_flow import FLOW
from deck_cases import CASES,TRANSFERS
from narration_application import APPLICATION

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'00_문서/이론덱'
SCHEDULE=json.loads((ROOT/'30_기록/일정원본.json').read_text(encoding='utf-8'))
KEYS={'실전반':['A','B','C','D','E','J','K','M'],'통합반':['A','F','G','H','I','N','J','K','L','O','P']}
DATES={'실전반':['2026-10-31','2026-11-07','2026-11-21','2026-11-28','2027-01-25','2027-01-26','2027-01-27','2027-01-28'],
       '통합반':['2026-11-14','2027-01-25','2027-01-26','2027-01-27','2027-01-28','2027-01-29','2027-02-01','2027-02-02','2027-02-03','2027-02-04','2027-02-04']}
PRACTICE={
 'A':'표의 의미와 관계를 정하고 우리말 질문의 계산 근거를 확인합니다.',
 'B':'원천별 품질 문제를 구별하고 처리 전후와 열 뜻의 근거를 확인합니다.',
 'C':'명세로 차트와 리포트를 만들고 계산과 설명을 같은 근거에 연결합니다.',
 'D':'규칙별 알람과 적용 범위를 만들고 놓친 변화와 반복 통지를 구별합니다.',
 'E':'수집·변환·감지·저장을 연결하고 입력 부족과 재실행을 드러냅니다.',
 'F':'판별 목표와 분할을 정하고 혼동 행렬로 모델 결과를 판단합니다.',
 'G':'정상 기반 비전 모델을 비교하고 이미지 판정의 대상과 한계를 설명합니다.',
 'H':'샷 순서와 시간 축을 구별하고 규칙·구간 비교·예측 기반 감지를 연결합니다.',
 'I':'RUL 방법과 합성 임계 도달 예측을 구별하며 정비 판단의 한계를 설명합니다.',
 'J':'문서를 읽고 검색·생성·관계 조회를 연결하며 근거 부족을 드러냅니다.',
 'K':'질문셋과 근거 평가로 수정 전후를 비교하고 모델별 요청을 관찰합니다.',
 'L':'영속 상태·연결·비밀을 구별해 서비스의 배포와 재시작 확인을 설계합니다.',
 'M':'도구와 기존 노드를 연결하고 승인된 변경 뒤의 결과를 다시 읽습니다.',
 'N':'감지·예측 성능을 비교하고 수집부터 결과까지 명세와 회귀 검사를 연결합니다.',
 'O':'업무별 도구와 상태 계약을 정하고 기존 노드·후속 질문·중단 조건을 연결합니다.',
 'P':'제안·승인·기록·재관측을 연결하고 승인 버전과 중복 효과를 확인합니다.'}
BRIDGES={
'A':['행의 단위를 알았으니 각 열이 무엇을 측정했는지 확인해야 합니다.','열의 뜻이 정해지면 질문을 어떤 계산으로 바꿀지 볼 수 있습니다.','계산할 값이 여러 표에 흩어져 있으면 같은 대상을 연결해야 합니다.','표를 잇는 이유를 적으면 데이터 밖의 부품 관계도 표현할 수 있습니다.','대상의 관계를 찾았어도 최근이라는 말의 기준은 따로 필요합니다.','대상과 기준을 정했으니 처음 답과 수정한 답을 같은 질문으로 비교할 수 있습니다.','개선의 이유를 설명하는 순서는 제조가 아닌 주제에서도 다시 쓸 수 있습니다.'],
'B':['오류를 가르려면 먼저 값이 없는 경우와 실제 0을 구별해야 합니다.','값의 존재를 확인한 다음에는 단위와 원천 표기를 맞춰야 합니다.','표기를 맞춰도 같은 값이 여러 번 보이는 이유는 따로 살펴야 합니다.','중복을 구별한 뒤에는 어떤 집단을 기준으로 삼을지 정해야 합니다.','기준 밖의 흔들림을 줄이는 처리도 실제 변화를 바꿀 수 있습니다.','수치 처리를 살폈으니 이제 열의 뜻을 모델이 제안하는 경우를 보겠습니다.','초안을 검수한 결과는 목적별 품질 판단으로 이어집니다.'],
'C':['보려는 질문을 골랐으니 그림의 가로축이 무엇인지 정해야 합니다.','축을 정해도 모든 점을 한 화면에 담는 과정에서 정보가 줄어듭니다.','원본을 확인할 수 있어도 비교 조건이 다르면 다른 결론이 나옵니다.','이 조건들을 만들기 전에 적어 두면 구현 결과를 확인할 기준이 됩니다.','명세의 한 문장을 작은 검사 항목으로 나누면 실패 이유가 보입니다.','검증한 계산을 역할에 맞는 보고 문장으로 옮겨 보겠습니다.','리포트까지 확인한 절차 중 반복되는 부분은 다음 작업에 재사용할 수 있습니다.'],
'D':['이상이 기준에서 벗어난 것이라면 먼저 그 기준의 출처를 봐야 합니다.','고정된 범위 외에도 자기 조건에서 얼마나 바뀌었는지 볼 수 있습니다.','한 값의 변화만으로 부족하면 같은 구간의 여러 조건을 함께 봅니다.','조건을 세웠어도 경계를 어디에 두느냐에 따라 선택 대상이 달라집니다.','선택된 알람을 실제로 읽으려면 같은 사건의 반복도 정리해야 합니다.','통지 정책과 판정 기준이 바뀌는 이력을 남겨야 전후를 설명할 수 있습니다.','규칙을 관리할 수 있어도 한 점의 크기만으로 보이지 않는 변화가 남습니다.'],
'E':['여러 단계가 이어지려면 각 단계가 주고받을 조건이 필요합니다.','조건을 정한 흐름을 다시 실행할 때 같은 사건이 중복되지 않아야 합니다.','재실행 결과가 다르면 어느 단계부터 달라졌는지 찾아야 합니다.','처리 경로를 확인했으니 여러 변수를 함께 보는 감지 방법을 넣어 봅니다.','현재 패턴의 낯섦과 미래 값의 예상은 다른 문제입니다.','서로 다른 방법의 결과는 같은 입력과 데이터 성격으로 비교해야 합니다.','비교한 결과를 다음 단계에 자동 전달할 때는 종료 조건도 필요합니다.'],
'F':['무엇을 맞힐지 정했으면 그 시점에 알 수 있는 입력을 골라야 합니다.','올바른 입력을 골라도 학습과 시험이 섞이면 사용 상황을 재현하지 못합니다.','분할한 표의 범주 수가 크게 다르면 정확도를 조심해서 읽어야 합니다.','전체 정확도에 숨은 놓침과 오탐을 네 칸으로 펼쳐 보겠습니다.','오류 방향을 알았으니 업무 비용에 맞는 경계를 고를 수 있습니다.','그런데 실제 검사 라벨이 없는 자료에서는 목표를 다시 정의해야 합니다.','라벨의 뜻이 달라지면 서비스에 저장할 판정의 의미도 달라집니다.'],
'G':['숫자를 그림으로 읽었으니 정답 라벨이 어떤 검사를 뜻하는지 보겠습니다.','검사 목표를 알면 정상만 배우는 방법을 어디에 쓸지 판단할 수 있습니다.','정상과 다르다고 본 위치를 히트맵으로 살펴보겠습니다.','모델이 본 차이는 결함뿐 아니라 촬영 조건에서도 생깁니다.','입력 조건을 맞춘 뒤 점수를 실제 판정으로 나누는 기준이 필요합니다.','같은 판정 기준과 입력 조건으로 다른 방법도 비교할 수 있습니다.','선택한 모델의 결과를 실제로 연결 가능한 대상에 저장해야 합니다.'],
'H':['순서의 의미를 알았으니 비교할 앞 구간의 범위를 정하겠습니다.','기준 구간이 정해지면 현재값의 벗어남을 수치로 표현할 수 있습니다.','그런데 비교 기준 자체가 변화를 따라갈 수도 있습니다.','현재값과 평균의 차이가 작다면 구간 사이의 차이를 볼 수 있습니다.','구간 차이와 별도로 과거에서 미래를 예상해 비교하는 방법도 있습니다.','어느 방법이든 입력값이 없으면 같은 판정을 이어 갈 수 없습니다.','입력과 판정 상태를 구별했으니 다음 판단으로 전달할 수 있습니다.'],
'I':['정비 시점을 예상하려면 수명이 끝난다는 뜻부터 정해야 합니다.','종료 조건이 있어도 관측이 끝난 기록과 실제 고장 기록은 다릅니다.','고장 끝을 모르는 자료에서는 예측 목표를 확인 가능한 것으로 좁혀야 합니다.','임계 도달 시점과 일정 기간의 사건 확률도 서로 다른 출력입니다.','확률이든 시점이든 결과가 얼마나 불확실한지 함께 살펴야 합니다.','불확실성을 알면 어떤 추가 점검과 승인이 필요한지 판단할 수 있습니다.','마지막으로 어떤 자료에서 확인한 계획인지 범위를 정리하겠습니다.'],
'J':['특정 자료의 답이 필요하니 먼저 관련 문서를 찾아 요청에 넣어야 합니다.','문서를 찾으려면 원본의 글과 표를 올바르게 읽는 과정이 앞섭니다.','읽어 낸 자료를 검색 단위로 나눌 때도 조건과 예외를 유지해야 합니다.','조각을 만들었으니 의미로 찾기 위한 표현을 살펴보겠습니다.','의미가 비슷한 것 외에 문서번호처럼 정확한 단서도 필요합니다.','검색을 고쳐도 계산과 여러 대상의 관계는 다른 경로가 필요합니다.','여러 경로에서 모은 근거가 최종 주장을 실제로 지지하는지 확인해야 합니다.'],
'K':['업무 질문을 정했으니 검색과 생성 중 어디를 평가할지 나누겠습니다.','답변 평가에서 특히 인용이 있다는 것과 주장을 지지한다는 것을 구별해야 합니다.','주장을 지지하는 문서라도 지금 적용되는 버전인지 확인해야 합니다.','이 기준을 모델에게 심사시키더라도 심사 오류는 남을 수 있습니다.','평가의 한계를 알았으니 같은 조건으로 모델 둘을 비교하겠습니다.','모델별 요청을 읽으면 무엇을 유지하면서 줄일지 판단할 수 있습니다.','요청을 바꾼 뒤에도 기존에 지키던 성질을 다시 확인해야 합니다.'],
'L':['접속 환경이 바뀌면 프로그램 실행 환경도 함께 준비해야 합니다.','실행 환경을 포장했어도 사라지면 안 되는 기록은 따로 보관해야 합니다.','영속 저장 위치를 정했으니 구조와 내용을 실제로 옮기는 과정을 봅니다.','저장소와 모델에 연결할 인증 정보도 환경에 맞게 전달해야 합니다.','연결을 구성했으니 상태 응답과 실제 업무를 나누어 확인하겠습니다.','기능이 동작해도 요청이 늘어나는 상황에서는 대기와 비용을 살펴야 합니다.','운영 조건을 읽을 수 있어야 다음 버전을 배포하고 다시 확인할 수 있습니다.'],
'N':['개선 목표를 정했으니 어떤 실패가 그 목표를 막는지 분류해야 합니다.','분류한 실패가 입력에서 생겼다면 모델보다 데이터를 먼저 고칩니다.','수정 후보를 정했으면 같은 조건에서 한 변경의 효과를 비교합니다.','비교를 반복할수록 설정 선택과 최종 시험을 나누어야 합니다.','선택한 모델도 서비스의 단계 계약에 맞게 연결돼야 합니다.','세 단계가 이어진 다음에는 기존 기능이 남아 있는지도 확인해야 합니다.','이 확인 절차를 다른 주제에서 재사용하려면 바뀌는 가정을 찾아야 합니다.'],
'O':['업무 에이전트가 일하려면 실제 기능에 실행을 요청하는 방식이 필요합니다.','도구마다 요청 방식을 새로 만들지 않도록 연결 규격을 사용할 수 있습니다.','연결 형식이 같아도 결과 상태의 의미는 업무에서 정해야 합니다.','결과의 의미가 정해지면 다음에 무엇을 할지 흐름으로 연결할 수 있습니다.','한 번의 흐름을 만든 뒤에는 후속 질문이 어떤 상태를 이어받는지 정해야 합니다.','상태를 이어받아도 근거가 부족하면 반복을 끝낼 조건이 필요합니다.','종료한 이유까지 요청 하나의 기록으로 되짚을 수 있어야 합니다.'],
'P':['한 바퀴의 범위를 정했으니 어떤 행동을 맡길지 업무별로 나눠야 합니다.','권한을 정한 뒤에는 제안이 그 약속을 지키는지 실행 전에 검사합니다.','검사를 통과해도 사람이 결정할 자리에서는 상태를 저장하고 기다려야 합니다.','대기 뒤 재개하려면 무엇을 승인했는지 정확히 식별해야 합니다.','승인 내용이 같아도 재시도에서 효과가 두 번 생기지 않아야 합니다.','한 번만 변경됐더라도 원하는 효과가 있었는지는 다시 측정해야 합니다.','확인한 효과와 남은 가설을 구별해 다음 판단의 근거로 남깁니다.'],
'M':['서비스 안의 에이전트는 도구에 실행을 요청해 업무를 수행합니다.','여러 도구를 공통 방식으로 연결할 때 MCP를 사용할 수 있습니다.','표준 연결이 되어도 빈 결과와 실패의 의미는 따로 정해야 합니다.','도구의 결과가 행동과 재관측까지 이어질 때 한 바퀴의 범위가 생깁니다.','행동이 다음 판단을 바꾸므로 실행 전에 지킬 약속을 검사해야 합니다.','약속을 통과한 제안도 승인 자리에서는 상태를 저장하고 기다립니다.','승인 뒤 바뀐 결과가 실제로 좋아졌는지는 다시 확인해야 합니다.']}
SOURCES={
 'schedule':'패키지 참고/KNU_PhysicalAI_uEngine.xlsx · 2_오프라인일정·3_영상제작·4_커리큘럼',
 'local':'패키지 실습흐름_정본.html 및 설계서/01·02·03·05 · 수업의 적용 설계',
 'data':'패키지 리서치/R5_실데이터_검증_KAMP예지보전_AIHub샘플.md · 제공자가 남긴 검증 기록, 이번 실행에서 원시 데이터를 재측정한 수치가 아님',
 'rag':'[Docling 공식 문서](https://docling-project.github.io/docling/) · [BGE-M3 모델 카드](https://huggingface.co/BAAI/bge-m3)',
 'eval':'[RAGAS 지표 목록](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/) · [Faithfulness 정의](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)',
 'ml':'[scikit-learn 분할·검증](https://scikit-learn.org/stable/modules/cross_validation.html) · [평가 지표](https://scikit-learn.org/stable/modules/model_evaluation.html)',
 'vision':'[Anomalib PaDiM](https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/models/image/padim.html) · [PatchCore](https://anomalib.readthedocs.io/en/latest/markdown/guides/reference/models/image/patchcore.html)',
 'timeseries':'[Chronos 공식 저장소](https://github.com/amazon-science/chronos-forecasting) · [PyOD 공식 저장소](https://github.com/yzhao062/pyod)',
 'rul':'[NASA C-MAPSS 데이터 설명](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data)',
 'cloud':'[Cloud Run 실행 계약](https://docs.cloud.google.com/run/docs/container-contract) · [Secret Manager 연결](https://docs.cloud.google.com/run/docs/configuring/services/secrets) · [Supabase 로컬 개발](https://supabase.com/docs/guides/local-development)',
 'agent':'[MCP 도구 사양](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) · [LangGraph interrupt](https://docs.langchain.com/oss/python/langgraph/interrupts) · [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)'}
REFS={'A':['data','local'],'B':['data','local'],'C':['local'],'D':['local','data'],'E':['timeseries','local'],
      'F':['ml','data'],'G':['vision','ml','data'],'H':['timeseries','ml','data'],'I':['rul','timeseries','local'],
      'J':['rag','local'],'K':['eval','local'],'L':['cloud','local'],'N':['ml','local'],'O':['agent','local'],'P':['agent','local'],'M':['agent','local']}
SOURCES['aas']='[IDTA AAS 개념 설명](https://industrialdigitaltwin.io/aas-specifications/IDTA-01001/v3.1.2/annex/concepts-aas.html)'
SOURCES['8d']='[ASQ 8D 단계 설명](https://asq.org/quality-resources/eight-disciplines-8d)'
REFS['A'].append('aas')
REFS['M'].append('8d');REFS['P'].append('8d')
BRIDGES['A'][1]='열의 뜻을 포함해 모델에 무엇을 맡길지 요청의 재료를 정하겠습니다.'
BRIDGES['A'].insert(2,'요청의 결과를 정했으니 질문을 실제 표의 계산으로 바꾸는 과정을 보겠습니다.')
BRIDGES['K']=[
 '업무 질문을 정했으니 검색과 생성 중 어디를 평가할지 나누겠습니다.',
 '네 관점 중 먼저 답이 질문 자체를 다루는지 살펴보겠습니다.',
 '질문에 직접 답하려면 검색한 후보에도 필요한 내용이 들어 있어야 합니다.',
 '관련된 것만 골랐어도 필요한 근거를 빠뜨렸을 수 있습니다.',
 '필요한 자료를 찾았으면 답의 각 주장이 그 자료에 기대고 있는지 확인합니다.',
 '주장을 지지하는 문서라도 지금 적용되는 버전인지 확인해야 합니다.',
 '이 기준을 모델에게 심사시키더라도 심사 오류는 남을 수 있습니다.',
 '평가의 한계를 알았으니 같은 조건으로 모델 둘을 비교하겠습니다.',
 '모델별 요청을 읽으면 무엇을 유지하면서 줄일지 판단할 수 있습니다.',
 '요청을 바꾼 뒤에도 기존에 지키던 성질을 다시 확인해야 합니다.']
BRIDGES['M'][6]='승인 대기 상태를 이어받듯 후속 질문에서도 현재 대상을 정확히 이어받아야 합니다.'
BRIDGES['M'].insert(7,'대상과 상태가 유지돼도 승인 뒤 바뀐 결과가 좋아졌는지는 다시 확인해야 합니다.')
BRIDGES['M'].append('확인한 결과와 아직 남은 가설을 구별해 다음 판단의 기록으로 남깁니다.')
EX_TITLES={('A',1):'압력처럼 보이는 열이 시간일 수 있습니다',('C',3):'같은 평균도 필터가 다르면 달라집니다',
 ('K',10):'수정 뒤에도 근거와 상태를 다시 검사합니다',('P',1):'조회·제안·변경의 권한을 나눕니다'}

def first(text):
    # 소수점에서 문장을 자르지 않는다.
    return re.split(r'(?<=[.!?])\s+',text.strip())[0].rstrip('.')

def slides_for(meta,key):
    topics=CAT[key]; flow=FLOW[key]; slides=[]
    def push(section,seconds,title,screen,visual,conclusion,bridge='',evidence='설계'):
        slides.append(dict(id=f'S{len(slides)+1:02}',section=section,seconds=seconds,title=title,
          screen=screen,visual=visual,conclusion=conclusion,bridge=bridge,evidence=evidence))
    transfer,objects,changes=TRANSFERS[key]
    practical=PRACTICE[key]
    class_intro=('센서의 숫자를 읽는 데서 시작해 판별·비전·예측을 같은 서비스로 이어 갑니다.' if meta['반']=='통합반' else
      '산업 데이터를 읽고 판단 근거를 쌓아 자기 서비스와 기업 과제로 이어 갑니다.')
    if key=='J': class_intro=('감지·예측 결과까지 연결했습니다. 이제 수치가 말하지 못한 배경을 문서에서 찾습니다.' if meta['반']=='통합반' else '규칙과 파이프라인이 확인한 변화를 바탕으로 관련 문서의 근거를 찾습니다.')
    if key=='K': class_intro='문서와 표, 관계를 연결해 답을 만들었습니다. 이제 어떤 질문에서 무엇이 맞는지 따로 확인합니다.'
    if key=='O': class_intro='배포한 서비스에 업무 도구를 연결합니다. 이 영상에서는 도구와 흐름을 다루고, 이어지는 영상11에서 승인·기록·재관측을 완성합니다.'
    if key=='P': class_intro='영상10에서 정한 도구와 상태 계약을 이어받습니다. 이번에는 제안이 승인된 행동과 다음 관측으로 이어지는 조건을 다룹니다.'
    push('도입',150,meta['제목'],[class_intro,practical],topics[0]['visual'],practical,'이 판단은 우리가 만들 서비스에서 어디에 쓰일까요?')
    push('도입',150,'이번 판단은 어디에 쓰일까요',[practical, f'같은 방법을 {transfer}에 쓰려면 {changes} 같은 항목을 새로 확인해야 합니다.',
        '화면 모양이 달라도 목적과 근거가 성립하면 서로 다른 구현을 만들 수 있습니다.'],
        f'{topics[0]["visual"]} 다음 장과 다른 시점에서 작업자가 해결할 질문과 결과 기록을 함께 보여 준다.',
        '무엇을 만들지와 어떻게 확인할지를 함께 생각합니다.',topics[0]['title'])
    concept_seconds=[5400//(len(topics)*3)+(i<5400%(len(topics)*3)) for i in range(len(topics)*3)]
    for i,t in enumerate(topics):
        example_title=EX_TITLES.get((key,i),first(t['example']))
        push('개념',concept_seconds[i*3],t['title'],[t['body']],t['visual'],t['title']+'.',example_title, '개념·근거')
        push('개념',concept_seconds[i*3+1],example_title,[t['example'],t['limit']],
          t['visual']+' 개념 장의 그림을 복제하지 않는다. 이번에는 사례의 대상·기록·조건을 가까이 보여 주고 수치가 있으면 원문대로 별도 텍스트로 얹는다.',
          t['limit'],t['question'],'근거 또는 명시된 설명용 예시')
        next_bridge=BRIDGES[key][i] if i<len(topics)-1 else '이제 이 판단들을 한 서비스의 적용 순서로 연결하겠습니다.'
        push('개념',concept_seconds[i*3+2],t['question'],[t['question'],t['answer']],
          f'판단 비교 삽화: {t["question"]} {t["visual"]} 질문에서 달라진 조건을 별도 새 장면으로 표현하고 정답 문장은 그림 밖 텍스트로 둔다.',
          t['limit'],next_bridge,'교육용 판단 예시')
    for i,f in enumerate(flow):
        push('적용 장면',200,f['title'],[f['input'],f['action']],
          f'새 적용 삽화. {f["input"]} {f["action"]} 읽는 사람이 입력에서 결과로 이동하는 경로를 한 장면에서 볼 수 있도록 실제 업무 기록·대상을 그린다. 제품 UI·터미널 캡처를 만들지 않는다.',
          first(f['action']),'이 변경이 제대로 됐는지는 어떤 결과로 확인할까요?')
        push('적용 장면',200,first(f['check']),[f['check'],
          f'다음 차이를 구별합니다. {f["failure"]}'],
          f'{f["title"]}의 결과 기록을 근접 촬영한 듯한 편집 삽화. 확인할 조건: {f["check"]} 현재 없는 성능값·성공 로그는 넣지 않고 조건과 대상의 대응을 보여 준다.',
          first(f['check']),f['failure'])
        next_flow=flow[i+1]['title'] if i<5 else '같은 원리를 다른 사례에 적용해 판단해 보겠습니다.'
        push('적용 장면',200,f['failure'],[f['failure'],f['repair']],
          f'같은 작업의 새로운 경계 사례를 그린다. 상황: {f["failure"]} 올바른 구별: {f["repair"]} 결과와 원인이 섞이지 않게 기록 위치를 구분한다.',
          f['repair'],next_flow,'교육용 설계·경계 사례')
    cases=list(CASES[key])+[
      dict(title='동작의 성공과 목표 달성을 구별합니다',
           situation=f'코딩 에이전트가 기능을 만들었다고 보고했습니다. 이번 기능은 다음과 같습니다. {practical} 화면은 열리지만 검토할 근거는 아직 모으지 않았습니다.',
           question='학생은 무엇을 확인한 뒤 다음 단계로 넘어갈 수 있을까요? 입력·결과·판단을 구분해 보세요.',
           answer=f'완료 보고나 화면 존재만으로 판단하지 않습니다. {flow[0]["check"]} 이어서 {flow[-1]["check"]} 형태가 다른 구현도 같은 성질로 확인합니다.'),
      dict(title=f'{transfer}에 같은 방법을 옮깁니다',
           situation=f'새 주제의 재료는 {objects}입니다. 기존 서비스와 같은 화면을 만들 필요는 없습니다.',
           question=f'{changes} 중 어떤 가정을 바꿔야 할까요? 그대로 쓸 절차 하나와 새로 확인할 기준 하나를 고르세요.',
           answer=f'새 대상에 맞는 판단 기준과 근거를 정의합니다. 다시 정할 항목은 {changes}입니다. 요구를 적고 결과를 대조하는 절차는 재사용할 수 있지만 제조 데이터의 키·단위·판정 의미를 그대로 가져오지 않습니다.')]
    for i,c in enumerate(cases):
        push('판단 연습',300,c['title'],[c['situation'],c['question']],
          f'교육용 사례의 구체적 업무 삽화: {c["situation"]} 비교에 필요한 기록과 조건만 넣는다. 회사명·인물명·실제 성능을 만들지 않는다.',
          c['question'],'선택한 이유를 자료와 연결해 확인하겠습니다.','교육용 가정')
        push('판단 연습',300,first(c['answer']),[c['answer'],
          '다른 선택을 했다면, 그 선택이 성립하려면 어떤 추가 조건이 필요한지 확인합니다.'],
          f'이전 문제 장을 복제하지 않고 판단의 결정적 근거를 확대한다. {c["answer"]} 문장은 독립된 큰 텍스트로, 삽화는 근거의 위치를 설명한다.',
          first(c['answer']),cases[i+1]['title'] if i<4 else '이 판단을 실제 실습에서 만들 기능의 요구로 옮기겠습니다.','교육용 해설')
    tasks=[
      ('맡길 기능의 목적을 정합니다',f'{practical} 이 중 사용자 한 사람이 할 일을 하나 고릅니다.',
       '누가 어떤 입력으로 어떤 결과를 얻으려는지 자기 말로 적습니다. 예시 화면을 그대로 복제하는 것을 목표로 삼지 않습니다.',
       '사용자·입력·필요한 결과를 구별할 수 있으면 다음 요구로 이어갑니다.'),
      ('입력과 근거를 확인합니다',f'필요한 자료: {flow[0]["input"]}',
       '실제로 가진 자료와 아직 없는 자료를 구별합니다. 이름·단위·식별자·라벨·문서 상태 중 이번 기능에 필요한 것을 확인합니다.',
       '없는 자료를 가정으로 채웠다면 교육용 가정임을 명시합니다. 필요한 원자료를 알 수 있어야 합니다.'),
      ('됐는지를 관찰 가능한 결과로 적습니다',f'확인할 성질: {flow[0]["check"]}',
       f'정상 입력의 결과와 다음 경계 사례를 구분해 봅니다. {flow[2]["failure"]} 구현 내부의 파일명 대신 보이는 동작과 근거를 적습니다.',
       f'{flow[2]["repair"]} 목적을 만족하는 다른 구현도 같은 기준으로 설명할 수 있어야 합니다.'),
      ('다음 실습의 첫 행동을 준비합니다',f'연결 실습일: {meta["실습일"]}. {practical}',
       '가이드의 현재 위치에서 필요한 설명과 자료를 보고 직접 구현 요청을 작성합니다. 이전 작업을 이어가거나 그 일차의 출발본으로 합류할 수 있습니다.',
       '오늘 입력에서 어떤 결과가 보여야 하는지 확인하고 첫 구현 요청을 자기 말로 작성합니다.')]
    for i,(title,situation,action,check) in enumerate(tasks):
        push('실습 준비',450,title,[situation,action,check],
          f'학습자가 자기 요구를 작성하는 작업대 삽화. {situation} 완성 프롬프트를 대신 써 놓지 않는다. 입력·결과·확인 자료를 구별한 여백을 둔다.',
          check,tasks[i+1][0] if i<3 else '처음에 맡기려던 판단으로 돌아가 결과를 정리합니다.','학습 활동 설계')
    push('회수·예고',150,'처음의 판단을 이제 설명할 수 있습니다',[practical,topics[-1]['limit'],
      '원하는 일을 맡기고, 나온 결과를 확인하고, 필요한 근거와 도구를 잇고, 아직 알 수 없는 범위를 설명합니다.'],
      f'도입과 동일한 주제이되 완전히 새 시점의 결말 삽화. {topics[0]["visual"]} 처음 비어 있던 기록 사이의 의미 있는 연결이 보이게 한다.',
      practical,'다음에는 이 결과를 어떤 판단의 입력으로 쓸까요?')
    next_info=('기업 데이터 적용 · 결과물 구축에서 새로운 대상과 근거에 맞게 다시 설계합니다.' if meta['반']=='실전반' and meta['영상번호']==8 else
      '영상11에서 도구의 제안을 승인·기록·재관측으로 이어 갑니다.' if key=='O' else
      '다음 PBL에서는 자기 문제의 입력·기준·근거·행동을 다시 정합니다.' if key=='P' else
      '연결 실습에서 오늘의 기준으로 자기 구현을 확인하고 다음 기능의 입력으로 사용합니다.')
    push('회수·예고',150,'다음 판단에 넘길 것은 결과와 근거입니다',[next_info,
      f'다른 주제에 남는 질문: {transfer}라면 {changes} 중 무엇을 다시 정해야 할까요?',
      '완성 모습이 같아야 하는 것은 아닙니다. 무엇이 되고 무엇이 아직 안 되는지 설명할 수 있어야 합니다.'],
      f'현재 작업의 결과 기록이 {transfer}의 새 작업대로 넘어가는 독창적 삽화. 옮길 수 있는 절차와 새로 정할 자료를 다른 물체로 표현.',
      '기술을 한 번 더 써서 자기 결과물을 만드는 것이 다음 목표입니다.','', '학습 연결 설계')
    for index,detail in enumerate(APPLICATION.get(key,[])):
        slide=slides[2+len(topics)*3+index]
        slide['screen'].append(detail['anchor'])
        slide['visual']+=' 설명의 중심에 다음 구분이 보이도록 자료의 위치와 대응을 구체화한다: '+detail['anchor']+' 핵심 문장은 이미지 안에 생성하지 말고 별도 텍스트로 배치한다.'
    assert len(slides)==36+len(topics)*3 and sum(s['seconds'] for s in slides)==14400
    return slides

def tc(sec):
    return f'{sec//3600:02}:{sec//60%60:02}:{sec%60:02}'

GUIDE='''## 제작 지시 — 화면에 넣지 않는 메타정보

이 파일은 NotebookLM용 슬라이드별 상세 원고다. 낭독 대본이나 완성 PPTX가 아니다. `화면 문구`의 의미와 인과를 보존하고 제목·결론·다음 장의 연결을 유지한다. `삽화·구성`과 `연결 문장`은 제작 지시이며 그대로 학생 화면에 복사하지 않는다. 화면의 설명은 자막 띠가 아니라 읽을 수 있는 문단·예시·비교로 구성한다.

16:9, 큰 한국어 제목과 읽기 쉬운 본문. 밝은 중성 배경에 청록·짙은 남색을 제한적으로 사용하되 참조 리허설의 도형·배치·디자인은 복제하지 않는다. 한 장에 충분한 설명을 남기고 글자를 줄여 맞추지 않는다. 삽화는 해당 물체·업무·인과가 정확한 독창적 편집 삽화로 제작한다. 장식용 로봇·회로·뇌 그림, 의미 없는 사각형 연결, 반복 카드 격자는 피한다. 실제 수치 그래프·표는 수치와 축을 정확히 유지한다. 생성 삽화에 글자를 맡기지 말고 제목·라벨·숫자는 별도 텍스트로 둔다.

`적용 장면`은 구현 원리를 설명하는 설계 스토리보드다. 실제 서비스 화면·실행 성공 로그·성능 측정치를 지어내지 않는다. 실물 캡처를 나중에 넣을 때는 해당 구현 버전에서 확인한 화면만 사용한다. 지금의 삽화는 설명용으로 완결되며 실제 앱 캡처의 대용 증거가 아니다.

시간은 엑셀 4H에 맞춘 집필 배분이며 녹화 길이나 학생 소요시간의 실측이 아니다. 판단 연습 시간에는 문제 읽기·비교·해설을, 실습 준비에는 예시를 따라 요구를 구체화하는 안내를 포함한다. 영상 일시정지 시간을 녹화 길이로 더하지 않는다. 낭독·녹화 후 실제 길이를 재고, 화면 밖 설명이 길어지는 곳은 필요한 장을 추가한다. 자료를 요약해 핵심 장을 제거하는 방식으로 맞추지 않는다.

근거 수치는 제공 패키지의 R5 보고에 귀속한다. 실제 파일을 이번에 다시 측정했다는 표현을 쓰지 않는다. 설명용 숫자와 교육용 가정은 화면에도 그 성격을 표시한다. 처음 나오는 용어는 원고의 정의를 보존하고 이후에는 같은 용어를 사용한다. 성능·비용·모델 비교의 미측정 값을 임의로 채우지 않는다.
'''

def render(meta,key,slides,subset=None):
    concept_end=2+len(CAT[key])*3
    apply_end=concept_end+18;case_end=apply_end+10;prep_end=case_end+4
    lines=[f'# {meta["반"]} {meta["영상"]} · {meta["제목"]}',
      f'\n- 연결 실습일: {meta["실습일"]}\n- 제작 마감: {meta["마감"]}\n- 엑셀 배포일: {meta["배포"]}\n- 시수: 4H · 전체 {len(slides)}장 · 계획 240분\n- 대상: 비컴공 대학생 · 직접 코딩보다 요구 작성·판단·활용에 집중\n- 실습 연결: {meta["실습명"]}',GUIDE,
      f'\n## 시간 배분\n\n| 구간 | 시간 | 장 | 진행 내용 |\n|---|---:|---|---|\n| 도입 | 5분 | S01–S02 | 해결할 판단과 결과 |\n| 개념 | 90분 | S03–S{concept_end:02} | 정의·사례·해석 한계 |\n| 적용 장면 | 60분 | S{concept_end+1:02}–S{apply_end:02} | 입력·만들 동작·결과 확인·경계 사례 |\n| 판단 연습 | 50분 | S{apply_end+1:02}–S{case_end:02} | 새 사례 5개와 해설 |\n| 실습 준비 | 30분 | S{case_end+1:02}–S{prep_end:02} | 목적·입력·확인 기준·첫 행동 |\n| 회수·예고 | 5분 | S{prep_end+1:02}–S{len(slides):02} | 도입 회수와 다음 판단 |']
    if subset: lines.append(f'\n이 분할 파일의 제작 범위는 {subset[0]}–{subset[-1]}이다. 전체 덱의 해당 번호만 제작한다. 표지·목차·마지막 정리 장을 임의 추가하지 않는다. 앞뒤 연결을 유지한다.')
    lines.append('\n## 장별 원고')
    elapsed=0
    for i,s in enumerate(slides):
        begin=elapsed;elapsed+=s['seconds']
        if subset and s['id'] not in subset: continue
        next_title=slides[i+1]['title'] if i+1<len(slides) else '다음 실습 또는 PBL'
        lines.extend([f'\n### {s["id"]} · {s["title"]}',
          f'\n**구간·시간** {s["section"]} · {tc(begin)}–{tc(elapsed)} · {s["seconds"]//60}분 {s["seconds"]%60:02}초',
          '\n**화면 문구**\n\n'+'\n\n'.join(s['screen']),
          f'\n**삽화·구성** {s["visual"]}',
          f'\n**이 장의 결론** {s["conclusion"]}',
          f'\n**연결 문장** {s["bridge"] or "이번 덱의 끝. 다음 실습에서 자기 결과물에 적용한다."}',
          f'\n**다음 장 제목** {next_title}',
          f'\n**근거·성격** {s["evidence"]}. 아래 출처의 해당 개념과 패키지의 대응 회차를 참고한다. 예시와 판단 기준은 교육용 설계이며 실제 수행 결과가 아니다.'])
    lines.append('\n## 출처 — 제작 참고, 학생 화면의 필요한 주장 근처에 짧게 표기\n\n- '+SOURCES['schedule']+'\n- '+'\n- '.join(SOURCES[r] for r in REFS[key]))
    lines.append('\n공식 기술 자료는 2026-09-14에 확인했다. 라이브러리 버전·제품의 최신 성능·가격을 확정하는 문서가 아니다. 패키지 원본은 프로젝트의 `30_기록/원자료/경남대_피지컬AI_협업패키지_20260912/`에 보존되어 있다.\n')
    return '\n'.join(lines)

def main():
    previous=ROOT/'30_기록/덱_매니페스트.json'
    if previous.exists():
        for record in json.loads(previous.read_text(encoding='utf-8')):
            path=ROOT/record['path']
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
                raise ValueError('전체 덱의 현재 편집을 먼저 확인하세요: '+str(path))
            for number,name in enumerate(record['parts']):
                ids=[s['id'] for s in record['slides'][number*12:(number+1)*12]]
                part=ROOT/name
                if not part.exists() or part.read_text(encoding='utf-8')!=render(record['meta'],record['key'],record['slides'],ids):
                    raise ValueError('분할 덱의 현재 편집을 먼저 확인하세요: '+str(part))
    manifests=[]
    for row in sorted(SCHEDULE['videos'],key=lambda r:(r['D'],int(r['E'].replace('영상','')))):
        klass=row['D'];num=int(row['E'].replace('영상',''));key=KEYS[klass][num-1];date=DATES[klass][num-1]
        off=next(r for r in SCHEDULE['offline'] if r['B']==date and r['E'].startswith(klass))
        meta={'반':klass,'영상':row['E'],'영상번호':num,'제목':row['G'],'마감':row['B'],'배포':row['C'],'실습일':date,'실습명':off['J'],'엑셀행':row['row']}
        slides=slides_for(meta,key)
        fn=f'영상{num:02}_{row["G"]}.md';path=OUT/klass/fn;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(render(meta,key,slides),encoding='utf-8')
        # 12장은 도구의 보장 한계가 아니라 검토하기 편한 제작 단위다.
        parts=[]
        for j in range(0,len(slides),12):
            ids=[s['id'] for s in slides[j:j+12]]
            part=OUT/'NotebookLM_분할입력'/klass/f'영상{num:02}'/f'{j//12+1:02}_{ids[0]}-{ids[-1]}.md'
            part.parent.mkdir(parents=True,exist_ok=True);part.write_text(render(meta,key,slides,ids),encoding='utf-8');parts.append(str(part.relative_to(ROOT)))
        manifests.append(dict(meta=meta,key=key,path=str(path.relative_to(ROOT)),parts=parts,
          slides=slides,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (ROOT/'30_기록/덱_매니페스트.json').write_text(json.dumps(manifests,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'decks':len(manifests),'slides':sum(len(m['slides']) for m in manifests),'parts':sum(len(m['parts']) for m in manifests),'minutes':sum(sum(s['seconds'] for s in m['slides']) for m in manifests)/60},ensure_ascii=False))

if __name__=='__main__':main()

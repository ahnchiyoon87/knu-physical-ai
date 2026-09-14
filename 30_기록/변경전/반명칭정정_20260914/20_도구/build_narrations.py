"""Build only authored concept sets; absent sets remain explicitly outstanding."""
import hashlib
import json
from pathlib import Path

from deck_content import CAT
from deck_flow import FLOW
from deck_cases import CASES,TRANSFERS
from narration_core import CORE
from narration_core import add
from narration_models import populate
populate(add)
from narration_rag import populate as populate_rag
populate_rag(add)
from narration_operations import populate as populate_operations
populate_operations(add,CORE)
from narration_application import APPLICATION
from narration_case_review import CASE_NARRATION

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'00_문서/대본'
MANIFEST=ROOT/'30_기록/대본_매니페스트.json'

SCENE={
'A':[
'샷 한 행과 LOT 설정 한 행을 같은 크기의 사건처럼 놓으면 연결이 꼬입니다. 먼저 각 원천의 이름을 카드처럼 구분합니다. 표의 머리글에는 사람이 읽을 뜻과 단위를 두고, 원본 이름도 찾아볼 수 있게 합니다. 파일에 없는 LOT를 붙일 때는 생성 규칙을 함께 남깁니다. 처음 기능을 만들 때부터 이 구분이 보이면 다음 질문에서도 같은 원천을 선택할 수 있습니다.',
'질문 칸이 답 문장만 보여 주면 학생은 어떤 계산을 했는지 알기 어렵습니다. 여기서는 사용한 열과 범위를 답 옆에서 읽는 구조를 만듭니다. 복잡한 SQL을 외우라는 뜻은 아닙니다. 어떤 열을 평균냈고 무엇으로 묶었는지 설명할 수 있어야 합니다. 화면에서 확인할 결과를 먼저 정하면 에이전트에게 구현을 맡길 때도 기준이 생깁니다.',
'수정할 실패를 하나 골랐습니다. 이름만 보고 고른 것이 문제라면 뜻과 단위를 제공하는 변경을 시험합니다. 결과가 마음에 들지 않는다는 말 대신 질문과 선택 열의 차이를 지목합니다. 같은 질문을 다시 사용해야 이번 변경이 무엇을 바꿨는지 읽을 수 있습니다. 처음부터 맞았던 질문도 몇 개 함께 확인하면 다른 조건을 깨뜨리지 않았는지 볼 수 있습니다.',
'샷 하나가 두 개정의 조건표와 동시에 연결되면 결과표에 두 번 나타날 수 있습니다. 평균은 우연히 그대로인데 합계가 늘어나는 경우도 있어서 숫자 하나로 연결 성공을 판단하지 않습니다. 적용할 개정과 키의 중복을 먼저 확인합니다. 조인 결과의 행 수를 원래 샷 수와 비교하는 작은 확인이 나중의 보고서 오류를 막는 데 도움이 됩니다.',
'모델에게 실제 코드값을 알려 주지 않으면 익숙한 표현을 골라 SQL에 넣을 수 있습니다. NG, N, 불합격은 사람이 비슷하게 읽어도 DB에서는 다른 문자열입니다. 작은 조회로 현재 저장된 값을 보고 어떤 뜻인지 연결합니다. 최근의 기준도 파일 마지막 관측에서 읽습니다. 정찰의 결과가 부족하거나 일부만 표시됐다면 전체 목록이라고 말하지 않습니다.',
'지도는 질문에 필요한 관계부터 시작합니다. 지금 볼 대상은 기계·부품·측정값·생산 묶음이며 서로의 역할이 다릅니다. 데이터 패브릭이라는 현업 개념은 여러 원천을 공통 의미와 접근으로 다루는 넓은 방향입니다. 여기서 만든 로컬 표 적재와 CSV 관계도를 그 전체 구현이라고 부르지 않습니다. 작은 서비스에서 배운 의미 연결을 더 큰 환경에 적용할 다음 학습 방향으로 이해합니다.'],
'B':[
'품질 카드의 첫 역할은 무엇이 관측됐는지 나누어 보여 주는 것입니다. 어떤 열에 결측이 있고 어느 열이 모두 같은 값인지 먼저 셉니다. 모델이 그 숫자를 추측하지 않고 실제 표를 코드로 집계하게 합니다. 이 단계에서 원인 설명을 자동으로 붙이기보다 어떤 원문과 기록을 더 봐야 하는지 남깁니다.',
'전체 평균을 기준으로 본 결과와 LOT 조건을 기준으로 본 결과가 달라질 수 있습니다. 둘 중 숫자가 적게 나오는 쪽을 무조건 고르지 않습니다. 우리가 찾으려는 변화가 같은 설정 안의 이탈인지, 전체 생산 조건의 차이인지 먼저 정합니다. 기준을 바꿨다면 그 정의와 분모도 결과에 함께 보입니다.',
'새 원천에는 다른 이름과 코드가 들어올 수 있습니다. 원본을 보존한 채 어떤 보기에서 무엇을 바꿨는지 정합니다. 단위를 바꾼 값과 의심만 표시한 값을 구분하고, 이유가 없는 자동 삭제는 하지 않습니다. 두 원천의 품질 숫자를 비교할 때도 같은 항목을 같은 정의로 센 것인지 확인합니다.',
'열 뜻을 작성하는 모델의 출력은 완성된 사전이 아니라 초안입니다. 원문 인용이 있는지와 그 인용이 뜻을 지지하는지 차례로 봅니다. 채택하지 않은 초안도 왜 제외했는지 구분할 수 있으면 다음 요청을 고칠 재료가 됩니다. 미확인 상태를 허용하는 것이 거짓 확신보다 유용합니다.',
'요약 점수와 기능의 필수 입력을 같이 둡니다. 여러 열이 깨끗해도 지금 분석에 필요한 열이 없으면 그 기능은 진행할 수 없습니다. 점수를 높이기 위해 검사 항목을 빼거나 분모를 바꾸지 않습니다. 어떤 목적에서 사용 가능한지 판단이 보이도록 화면을 구성합니다.',
'다른 자료로 옮겨도 원본·처리 규칙·사용 목적을 구분하는 순서는 남습니다. 원천마다 다른 코드와 단위는 다시 확인해야 합니다. 새 데이터가 기존 표와 비슷해 보인다는 이유만으로 같은 정제 규칙을 적용하지 않습니다. 결과를 설명할 수 있는 연결을 유지하는 것이 재사용의 기준입니다.']}


def sentence(text):
    return text.rstrip(' .')+'.'


def spoken(record,index):
    meta,key,slides=record['meta'],record['key'],record['slides']
    slide=slides[index];topic_end=2+len(CAT[key])*3
    transfer,objects,changes=TRANSFERS[key]
    if index==0:
        return f"이번 영상의 주제는 {meta['제목']}입니다. 화면에서 앞으로 만들 기능의 목적을 먼저 보겠습니다. {slides[0]['screen'][0]} 이 과정에서 코딩 에이전트는 코드를 만드는 일을 돕고, 여러분은 무엇을 만들지와 어떤 결과가 맞는지 정합니다.\n\n{slides[0]['screen'][1]} 자료가 있어도 질문의 기준이 빠지면 그럴듯한 오답을 만들 수 있습니다. 그래서 기능의 이름보다 입력·판단·근거가 어떻게 이어지는지 따라가겠습니다. 용어는 처음 필요한 자리에서 뜻을 설명하고 그다음부터 같은 용어로 사용합니다. 오늘의 설명을 모두 외우기보다 자신의 결과를 확인할 질문을 하나씩 가져가면 됩니다.\n\n마지막에는 {meta['실습일']} 실습에서 먼저 할 일을 정합니다. 강의의 사례는 설명을 위한 것이며 실제 실행 결과와 구분합니다. 화면의 수치가 제공 원자료의 보고인지 교육용 가정인지도 함께 읽겠습니다."
    if index==1:
        return f"어디에 쓸지 알면 무엇을 배워야 할지도 선명해집니다. 지금 서비스에서 필요한 판단은 화면 첫 문장에 있습니다. {slides[0]['screen'][1]} 단순히 버튼이 하나 늘어나는 것보다 사용자가 결과의 범위와 근거를 읽을 수 있는지가 중요합니다.\n\n이 방법을 {transfer}에 옮긴다고 생각해 보겠습니다. 재료는 {objects}입니다. 프로그램을 만드는 도구는 재사용할 수 있지만 {changes}은 새 주제에서 다시 정해야 합니다. 제조에서 맞던 번호나 기준을 이름만 바꿔 가져오면 의미가 달라진 계산이 남을 수 있습니다.\n\n오늘은 원하는 일을 맡기고, 결과를 확인하고, 필요한 자료를 연결하고, 아직 알 수 없는 것을 설명하는 순서로 갑니다. 서로 다른 화면을 만들어도 같은 목적과 근거가 성립하면 됩니다. 그 출발이 다음 장의 첫 개념입니다."
    if index<topic_end:
        topic,part=divmod(index-2,3)
        return CORE[key][topic][part]
    if index<topic_end+18:
        if key in APPLICATION:
            return APPLICATION[key][index-topic_end]['spoken']
        unit,part=divmod(index-topic_end,3);flow=FLOW[key][unit]
        scene=SCENE.get(key,[])
        if part==0:
            detail=scene[unit] if unit<len(scene) else flow['action']
            return f"이제 앞에서 배운 판단을 실제 기능의 순서로 옮겨 보겠습니다. {flow['input']}\n\n{detail}\n\n학생은 원하는 행동과 확인 기준을 정하고 실제 코드 작성은 코딩 에이전트에게 맡깁니다. 이번 장면에서 요청할 동작은 다음과 같습니다. {flow['action']} 화면의 입력과 만들 결과를 각각 짚어 보면 어떤 정보를 먼저 준비해야 할지 보입니다. 구현을 마쳤다는 말만 기다리지 않고 다음 장에서 볼 확인 결과까지 요청에 포함합니다."
        if part==1:
            return f"방금 요청한 기능이 만들어졌다면 어디를 볼까요? {flow['check']}\n\n화면에 적힌 확인 기준을 실제 입력과 결과 사이에 놓아 보겠습니다. 입력이 다른데 결과 모양만 같으면 같은 확인이 아닙니다. 결과가 같은 수치로 보이더라도 사용한 범위와 근거가 다를 수 있습니다. 필요한 정보가 화면에 없으면 우선 그 연결을 보이게 만듭니다.\n\n이 확인의 경계도 함께 생각합니다. {flow['failure']} 이 질문에 답하려면 첫 단계의 입력과 마지막 결과를 같이 읽어야 합니다. 에이전트가 보고한 완료와 여러분이 확인한 성질을 구분한 뒤, 다음 장의 실패 조건에서 무엇이 달라지는지 살펴보겠습니다."
        return f"지금은 성공한 모습의 반대쪽을 보겠습니다. {flow['failure']}\n\n{flow['repair']} 앞 장에서 정한 확인 기준을 다시 이 상황에 대입하면 빠진 조건이 드러납니다. 잘못된 결과를 보기 좋게 바꾸는 것으로 끝내지 않고, 어떤 입력이나 관계를 다시 확인해야 하는지 정합니다.\n\n고친 뒤에는 방금 실패한 사례만 보지 않습니다. 먼저 되던 정상 사례가 같은 조건으로 남는지도 확인합니다. 실제로 실행하지 않은 결과는 미확인으로 두고, 실패를 정상값으로 바꿔 다음 단계에 넘기지 않습니다. 이 원칙을 유지한 상태에서 다음 기능으로 연결하겠습니다."
    if index<topic_end+28:
        number,part=divmod(index-topic_end-18,2)
        if key in CASE_NARRATION and number<len(CASE_NARRATION[key]):
            return CASE_NARRATION[key][number][part]
        if part==0:
            return f"이번에는 조건을 조금 바꾼 사례입니다. {slide['screen'][0]}\n\n{slide['screen'][1]} 바로 결론을 고르기 전에 화면에서 확실히 주어진 사실과 아직 없는 조건을 나눠 보겠습니다. 선택 하나가 성립하려면 어떤 입력이 필요하고, 다른 선택을 하면 어떤 결과가 달라지는지 생각합니다.\n\n우리가 앞에서 만든 기준을 이 사례에도 적용할 수 있는지 확인합니다. 익숙한 단어가 나온다는 이유로 이전 답을 그대로 쓰지 않습니다. 판단을 잠깐 정한 뒤 다음 장의 해설에서 그 이유를 대조하겠습니다."
        return f"선택의 이유를 확인하겠습니다. {slide['screen'][0]}\n\n이 해설은 결과 문장을 외우라는 답안이 아닙니다. 어떤 조건 때문에 판단이 갈리는지 읽어야 다음 사례에서도 사용할 수 있습니다. 다른 선택을 했다면 그 선택이 맞기 위해 추가로 필요한 자료나 가정을 말해 볼 수 있습니다. 필요한 조건이 화면에 없는데 확신한 것은 아닌지 확인합니다.\n\n이제 이 사례에서 확정할 수 있는 범위와 다음에 확인할 항목을 나눕니다. 같은 모양의 프로그램을 만드는 것보다 이 구분을 자신의 말로 설명하는 것이 중요합니다. 다음 사례에서도 입력·기준·근거를 함께 보겠습니다."
    if index<topic_end+32:
        number=index-topic_end-28
        flow=FLOW[key]
        texts=[
          f"이제 실습에서 맡길 일을 하나 고릅니다. {slides[0]['screen'][1]} 그중 사용자 한 사람이 실제로 할 작업을 좁혀 보세요. 처음부터 모든 화면을 요구하면 어느 결과를 확인해야 할지 흐려질 수 있습니다.\n\n사용자가 넣을 입력과 얻을 결과를 두 칸으로 나눠 말해 보겠습니다. 결과가 숫자인지, 근거가 있는 설명인지, 다음 행동의 제안인지도 정합니다. 에이전트에게 구현의 모든 방법을 알려 줄 필요는 없습니다. 다만 목적을 바꾸는 조건을 맡긴 채 잊어서는 안 됩니다.\n\n다음에는 그 요청을 만들 자료가 실제로 있는지 확인합니다. 목적이 정해져야 필요한 자료와 아직 불필요한 자료를 구분할 수 있습니다.",
          f"목적을 정했으니 실제 입력을 펼칩니다. {flow[0]['input']} 파일 이름만 보고 준비됐다고 하지 않고 필요한 열과 대상의 뜻을 확인합니다. 화면에 있는 자료와 나중에 받을 자료를 따로 둡니다.\n\n없는 값을 설명용으로 만든다면 교육용 가정이라고 표시합니다. 그 값으로 실제 설비 성능을 검증했다고 말하지 않습니다. 자료의 단위와 식별자, 적용 상태가 질문에 맞는지 확인하면 에이전트에게 전달할 입력도 더 분명해집니다.\n\n필요한 자료가 없어서 못 하는 기능은 조건 부족으로 표현합니다. 그것을 무조건 실패한 학습으로 볼 필요는 없습니다. 무엇이 더 필요한지 알게 된 것도 판단의 결과입니다.",
          f"됐는지를 눈에 보이는 성질로 바꾸겠습니다. {flow[0]['check']} 여기에 실패할 수 있는 입력을 하나 더 놓습니다. {flow[2]['failure']}\n\n정상 사례와 이 경계 사례에서 각각 어떤 결과를 기대할지 적습니다. 단순히 오류 없이 종료한다는 문장보다 어떤 입력이 어디까지 전달되는지 정하면 확인하기 쉽습니다. {flow[2]['repair']}\n\n이 기준을 만족하는 화면과 코드가 여러 가지일 수 있습니다. 강사의 참고 구현과 다르다는 이유만으로 틀렸다고 하지 않습니다. 같은 조건을 지키는지 설명할 수 있어야 합니다. 이제 이 기준으로 첫 요청을 준비합니다.",
          f"다음 실습일은 {meta['실습일']}입니다. 여러분의 프로젝트가 이어지면 그 작업을 사용하고, 중간에 빠졌거나 막혔다면 해당 일차의 출발본을 새 폴더에서 엽니다. 기존 작업은 보존합니다.\n\n가이드에는 행동 옆에 필요한 설명이 다시 들어 있습니다. 지금 배운 내용을 모두 기억해야 시작할 수 있는 구조가 아닙니다. 오늘 정한 목적과 입력, 확인 기준을 가지고 첫 구현 요청을 자신의 말로 작성하면 됩니다.\n\n에이전트의 이해가 다르면 그 자리에서 바로잡고, 결과가 나오면 미리 정한 기준으로 읽습니다. 안 되는 경우에는 첫 실패 지점과 부족한 조건을 찾습니다. 다음 장에서 처음의 질문으로 돌아가 오늘 무엇을 얻게 됐는지 정리하겠습니다."
        ]
        return texts[number]
    if index==len(slides)-2:
        return f"처음에는 무엇을 만들어야 할지부터 정했습니다. 이제 그 목적을 입력과 근거, 확인 기준으로 설명할 수 있습니다. {slides[0]['screen'][1]}\n\n오늘의 마지막 한계도 함께 기억하겠습니다. {CAT[key][-1]['limit']} 기능이 동작한다는 말보다 어떤 자료와 조건에서 무엇을 확인했는지가 더 정확한 설명입니다. 모르는 범위를 말할 수 있어야 다음 자료와 검사를 선택할 수 있습니다.\n\n코딩 에이전트에게 원하는 일을 맡기는 능력은 긴 프롬프트를 외우는 능력이 아닙니다. 나온 결과와 목적의 차이를 찾아 다음 요청으로 줄이는 능력입니다. 이 결과를 다음 판단의 입력으로 넘기겠습니다."
    return f"다음에 넘길 것은 결과만이 아니라 그 결과의 근거입니다. {slide['screen'][0]}\n\n{transfer}를 자신의 주제로 삼는다면 {changes}을 다시 확인해야 합니다. 같은 절차를 쓸 수 있는 부분과 새 자료가 필요한 부분을 나누어 보세요. 익숙해진 도구를 한 번 더 써서 자기 목적의 결과물을 만드는 것이 다음 목표입니다.\n\n오늘의 예시 화면과 같지 않아도 됩니다. 누가 어떤 입력으로 무엇을 할 수 있고 어디까지 확인했는지 설명할 수 있으면 됩니다. 그 질문을 가지고 실습에서 자신의 첫 동선을 만들어 보겠습니다."


def main():
    decks=json.loads((ROOT/'30_기록/덱_매니페스트.json').read_text(encoding='utf-8'))
    old=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {'written':[]}
    for item in old['written']:
        path=ROOT/item['path']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=item['hash']:
            raise ValueError('대본의 사용자 편집을 보호합니다: '+str(path))
    written=[];pending=[]
    for deck in decks:
        meta=deck['meta'];key=deck['key']
        if key not in CORE:
            pending.append({'group':meta['반'],'video':meta['영상'],'key':key});continue
        assert len(CORE[key])==len(CAT[key])
        path=OUT/meta['반']/f"영상{meta['영상번호']:02d}_{meta['제목']}_대본.md"
        lines=[f"# {meta['반']} {meta['영상']} · {meta['제목']} · 낭독 원고",'',
          '슬라이드의 화면 문구와 별도로 읽을 발화 원고입니다. 아래 발화만 낭독하고 화면 지시는 읽지 않습니다. 계획 시수는 4H지만 현재 원고의 낭독·녹화 길이는 아직 측정하지 않았습니다. 장별 분량과 화면 밖 설명을 검토하는 집필본이며, 녹화 시간 충족을 확인한 최종본으로 표시하지 않습니다.','',
          f"연결 덱: [슬라이드별 원고](<../../이론덱/{meta['반']}/{Path(deck['path'].replace(chr(92),'/')).name}>)",'',
          '화면 지시는 현재 MD 덱의 제목과 번호를 기준으로 합니다. 긴 설명을 화면 밖에만 남기지 않도록 필요한 근거·예시가 해당 장에 있는지 대조합니다. 실제 수치·실행 화면은 확인한 증거가 있을 때만 사용합니다.','']
        chars=0
        for i,slide in enumerate(deck['slides']):
            text=spoken(deck,i);chars+=len(text)
            lines += [f"## {slide['id']} · {slide['title']}",'',
              f"화면: {slide['section']} · 제목과 본문을 보여 준 뒤 사례의 대상·조건을 순서대로 짚습니다.",'',
              '### 발화','',text,'',
              '### 다음 장으로','',sentence(slide['bridge']) if slide['bridge'] else '이 영상의 끝입니다. 연결 실습에서 자기 결과물에 적용합니다.','']
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(lines),encoding='utf-8')
        written.append({'path':str(path.relative_to(ROOT)).replace('\\','/'),'hash':hashlib.sha256(path.read_bytes()).hexdigest(),
          'group':meta['반'],'video':meta['영상'],'key':key,'slides':len(deck['slides']),'spoken_characters':chars,
          'status':'집필본: 개념 발화 별도 작성, 적용·판단 발화의 반복과 분량 추가 검토 필요','duration_measured':False})
    MANIFEST.write_text(json.dumps({'written':written,'pending':pending},ensure_ascii=False,indent=2),encoding='utf-8')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'README.md').write_text('# 영상별 대본\n\n현재 집필본입니다. 전체 goal은 계속 진행 중이며 아래 작성 목록이 전체 완료를 뜻하지 않습니다. 녹화 길이 미측정, 적용·판단 구간의 발화 다양성과 화면 정합성 검토가 남아 있습니다.\n\n'+
        '\n대본의 대상은 온라인 이론만입니다. 실습·설치·현장 진행 대본은 만들지 않습니다. 통합반·4학년의 공통 내용은 원자료 반 명칭과 연결해 반영합니다.\n\n'+
        '\n'.join(f"- [{x['group']} {x['video']}](<{x['group']}/{Path(x['path']).name}>) · {x['slides']}장" for x in written)+
        '\n\n미작성: '+(', '.join(x['group']+' '+x['video'] for x in pending) or '없음. 집필본의 내용·분량 검토는 별도 진행 중')+'\n',encoding='utf-8')
    print(json.dumps({'written':len(written),'pending':len(pending),'slides':sum(x['slides'] for x in written)},ensure_ascii=False))


if __name__=='__main__':main()

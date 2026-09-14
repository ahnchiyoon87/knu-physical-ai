"""Questions and source-grounded instructor references; not model execution results."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'10_실습/완성본/equipment-assistant'
QUESTIONS=[
('시업 점검에서 남길 기록 항목은 무엇인가요?','SHIFT','점검 시점, 설비 식별자, 항목, 관측 결과, 조치 필요 여부를 기록하고 이전 교대 인계와 새 관측을 구분한다.'),
('공정 조건을 바꾼 뒤 첫 생산품은 무엇을 확인하나요?','FIRST','검사 대상·기준과 적용 규격의 개정 및 측정 결과를 확인한다. 사전 승인만으로 검사 합격을 대신하지 않는다.'),
('설정값이 같으면 자주검사에서 제품 관측을 생략해도 되나요?','PATROL','설정 일치와 제품 합격은 별개이므로 제품 관측을 생략하지 않는다.'),
('마지막 생산품이 합격이면 LOT 전체도 합격으로 봐도 되나요?','LAST','확인한 생산 범위에만 적용하며 중간 구간 전체로 확대하지 않는다.'),
('교대 때 아직 확인하지 못한 원인 후보를 어떻게 전달하나요?','HANDOVER','관측·조치 현황·미확인을 구분하고 원인 후보를 확정 원인으로 바꾸지 않는다.'),
('4M 변경 요청에는 어떤 범위를 적어야 하나요?','FOURM','사람·설비·재료·방법의 변경 대상, 목적, 영향 범위, 필요한 확인 항목을 적는다.'),
('승인 후 변경안 내용이 달라지면 이전 승인을 적용해도 되나요?','FOURM','이전 승인을 새 내용에 자동 적용하지 않고 추가 검토 필요 여부를 판단한다.'),
('변경 실행 요청의 응답이 없으면 실행하지 않은 것으로 볼까요?','CHANGE','응답 부재만으로 미실행을 단정하지 말고 저장된 실행 기록을 먼저 조회한다.'),
('서로 다른 원천의 LOT 번호가 같으면 같은 대상으로 연결하나요?','TRACE','원천이 다르면 같은 번호여도 별개이며 명시된 원천과 LOT 키로 연결한다.'),
('억제한 알람 관측은 삭제하나요?','ALARM','억제된 관측도 원본 이벤트에 남긴다. 억제는 통지 운영이며 관측 삭제가 아니다.'),
('규칙 변경의 효과를 어떤 입력으로 비교하나요?','RULE','동일하게 저장한 입력을 이전·새 규칙으로 재생하고 버전을 기록한다. 통지 감소만으로 품질 개선을 확정하지 않는다.'),
('보전 요청에서 일반적인 점검 후보를 어떻게 표현하나요?','MAINT','현재 설비의 확정 고장으로 적지 않고 확인할 항목과 추가 자료를 구분한다.'),
('측정값이 빠진 검사 항목은 합격으로 채우나요?','INSPECT','합격으로 채우지 않으며 미검사와 부적합을 구분한다.'),
('폐기 문서가 검색 1위면 현행 작업의 근거로 쓸 수 있나요?','DOCCTRL','검색 순위와 무관하게 적용 상태를 확인하고 폐기 문서를 현행 근거에 넣지 않는다.'),
('사람의 승인에 연결해야 할 대상 정보는 무엇인가요?','APPROVAL','제안 대상·내용·버전·근거·적용 범위를 읽고 승인 또는 반려 사유를 남긴다.'),
('이 공장의 실제 지난달 불량률을 알려 주세요.','','문서에 실제 공장의 지난달 생산·검사 통계가 없으므로 수치를 만들지 않는다.'),
('LOT 358의 고장 원인을 하나로 확정해 주세요.','','교육용 절차서만으로 특정 실제 사건의 원인을 확정할 수 없다.'),
('실제 사출기의 체크링은 몇 시간 뒤 고장 나나요?','','실제 고장 라벨·기준·장기 열화와 시각 정보가 없어 남은 시간을 확정하지 않는다.'),
('COND-B 표에서 조건 변경 기록에 필요한 항목과 확인 시점은 무엇인가요?','COND-B','변경 항목·전후 값·적용 대상·승인 기록을 변경 반영 전에 확인한다. 교육용 기록 항목표의 해당 행과 머리글을 함께 읽는다.'),
('COND-B 표에서 변경 후 첫 생산품 기록에는 누가 포함되며 언제 확인하나요?','COND-B','검사 대상·검사 결과·판단자를 기록하고 변경 반영 후 첫 생산품 확인 시 확인한다.')]


def main():
    student=[];teacher=[]
    for index,(question,doc,reference) in enumerate(QUESTIONS,1):
        identity=f'R{index:02d}'
        student.append({'id':identity,'question':question})
        teacher.append({'id':identity,'question':question,'expected_documents':[doc] if doc else [],
            'expected_statuses':['ok'] if doc else ['refused','insufficient'],'reference':reference,
            'reference_kind':'강사 작성 기대 근거. 모델 실행 답안 아님'})
    paths=[(ROOT/'10_실습/학생가이드/자료/RAG_질문20.json',student),
           (ROOT/'10_실습/강사용/RAG_질문20_기대근거.json',teacher),
           (APP/'evaluation/questions20_reference.json',teacher)]
    for path,value in paths:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    template=[{'id':f'Q{i:02d}','question':'','expected_documents':[],'expected_statuses':[], 'reference':''} for i in range(1,31)]
    path=ROOT/'10_실습/학생가이드/자료/내_질문30_작성틀.json';path.write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'10_실습/학생가이드/자료/질문셋_사용법.md').write_text('''# 질문셋을 쓰는 순서

RAG 일차의 질문20은 문제만 제공합니다. 문서에서 기대 근거를 찾고 맞음·틀림·지어냄·거절을 대조합니다. 모델이 실제로 낸 답은 실행 후에 별도 저장합니다. 강사 기대 근거를 모델 실행 결과라고 부르지 않습니다.

평가 일차에는 내_질문30_작성틀.json의 빈칸을 채웁니다. question은 자기 질문, expected_documents는 실제 문서 ID, expected_statuses는 허용할 상태, reference는 사람이 문서를 읽고 쓴 기준 답변입니다. 문서에 없는 질문은 문서 목록을 비우고 refused 또는 insufficient를 기대합니다. 질문과 상태가 빈 틀 그대로는 실행할 수 없습니다.

예: 문서가 지원하는 질문은 expected_statuses에 ok를 넣고 필요한 문서 ID를 넣습니다. 이 형식 안내는 어떤 질문의 정답을 대신 만들지 않습니다. 한 질문에 여러 근거가 필요하면 필요한 ID를 함께 정합니다.

같은 파일을 보존한 채 모델·검색 설정 하나를 바꿔 비교합니다. 질문 파일을 바꿨다면 다른 평가 조건으로 표시합니다. UI 평가에는 각 질문의 계약 항목이 필요하며, RAGAS까지 사용하면 reference도 필요합니다.
''',encoding='utf-8')
    print('학생 질문20·작성틀30·강사 기대근거20 작성')


if __name__=='__main__':main()

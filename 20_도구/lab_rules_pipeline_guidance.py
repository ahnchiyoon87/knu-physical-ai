"""Actions needed exactly where rules and pipeline are first constructed."""
RULES_PIPELINE_ACTION = {
('rules',0): """**실행 전에 오늘 기능을 만듭니다.** 출발본에는 분류까지 들어 있고 rules.json·seed_rules.py·감지 화면은 오늘 추가합니다. 입력은 synthetic의 shots로 되돌리고 conditions도 먼저 적재합니다. labeled는 어제의 분류표이며 오늘 규칙의 원천이 아닙니다. 쿠션은 열22, 계량시간은 열18, 조건표의 쿠션 기준은 열102입니다. 다른 원본에서는 자기 열 사전을 따릅니다.

세 규칙과 등록 스크립트가 만들어지면 프로젝트 루트에서 `uv run --env-file .env python scripts/seed_rules.py`를 실행합니다. created는 새 규칙 등록, preserved는 기존 규칙 보존입니다. rules.json을 고쳤다고 이미 등록된 규칙이 바뀌지는 않습니다. 서버와 화면을 다시 빌드/시작한 뒤 ‘현재 규칙 보기’로 실제 등록 정의와 버전을 읽고 감지합니다.

절대 기준은 각 LOT 조건표의 기준±1.5 mm를 모든 유효 관측에 댑니다. 상대·조합의 첫200행은 기준을 만드는 구간이고 판정 대상에서 제외합니다. 참고 결과의 input_rows는 전체 입력, baseline_rows는 기준에 사용한 행, missing_rows는 판정에서 빠진 결측, evaluated는 실제 판정한 행입니다. 성공 결과에서는 세 구간의 합이 input_rows와 맞아야 합니다. 규칙별 판정 구간 자체가 다를 수 있으므로 evaluated 숫자만 같다고 동일 비교로 보지 않습니다.""",
('rules',1): """**비교할 설정 두 개를 보존합니다.** 참고 규칙의 suppression_shots는 10입니다. 억제 없는 비교본은 같은 definition을 복사하고 새 id(예: cushion-relative-no-suppression)와 suppression_shots=0만 바꿔 추가합니다. seed_rules로 새 ID를 등록하고 두 ID의 정의를 다시 읽습니다. 이미 등록된 ID를 덮거나 뒤의 사람 승인 기능을 오늘 사용할 필요는 없습니다.

같은 원천·같은 규칙 계산·같은 행 구간에서 두 결과의 flagged를 비교하고 각 결과의 notified+suppressed=flagged를 확인합니다. 우선순위는 검토 순서를 위한 표시이며 값의 이상 여부를 바꾸는 계수가 아닙니다. 규칙 ID가 다르면 저장 사건의 method도 다릅니다. 이벤트 목록 전체 개수를 합쳐 통지가 두 배가 됐다고 해석하지 않습니다.""",
('rules',2): """**번호를 관계 대상 ID로 바꿉니다.** 합성 shots의 LOT4라면 시작은 `synthetic:shots:lot:4`, 끝은 `synthetic:worklog:lot:4` 또는 `synthetic:conditions:lot:4`입니다. 숫자4만 입력하지 않습니다. 먼저 관계표를 적재·대조하고 이 ID로 경로를 찾습니다.

오늘 패키지는 Neo4j 동기화 버튼을 제공하지 않습니다. 경보의 graph_status=queued는 나중에 반영할 기록을 만들었다는 뜻입니다. 관계표 경로가 보이는 것과 경보 노드가 그래프 DB에 반영된 것은 별개입니다. 오늘은 사건의 실제 LOT와 관계표 대상이 일치하는지 확인하고, DB 동기화는 RAG 단계에서 추가합니다.""",
('pipeline',0): """**먼저 예측 없는 연결을 만듭니다.** 코딩 에이전트에게 현재 적재와 규칙 함수를 순서대로 호출하는 scripts/reload.py를 작성하도록 요청합니다. 조건표 적재와 규칙 등록은 앞 단계에서 마친 상태여야 합니다. 참고 reload는 선택한 shots를 적재하며 conditions를 대신 적재하지 않습니다.

구현 후 프로젝트 루트에서 `uv run --env-file .env python scripts/reload.py --profile synthetic --source shots --rule cushion-relative`로 연결합니다. 최초 적재와 같은 파일 재실행을 구별하고, ingest의 duplicate와 감지 결과를 함께 봅니다. 중간에 멈추면 stopped_at과 completed에서 실패한 단계와 앞서 끝난 결과를 읽습니다. 앞 단계의 저장을 자동으로 되돌렸다는 뜻은 아닙니다. 현재 CSV 단계의 graph.status=not_applicable는 그래프 DB 반영 대상이 아니라는 뜻이며 ‘동기화 성공 0건’으로 바꾸지 않습니다. 이후 Neo4j 단계에서만 applied·remaining을 읽습니다.

파일 내용이나 매핑이 달라진 입력은 같은 source_id로 덮어 적재할 수 없습니다. 새 CSV를 등록하려면 새 원천 ID와 중복되지 않는 table 이름, 그 원천을 가리키는 새 규칙 ID를 정합니다. 이 정책은 기존 결과를 보존하기 위한 것이며 자동 증분 적재를 구현한 것으로 표현하지 않습니다.""",
('pipeline',1): """**누락 사례는 현재 자료를 건드리지 않고 만듭니다.** 에이전트에게 작은 조건표 행 목록을 넣는 검사를 요청하면 DB를 새로 만들지 않고도 누락·중복 조건에서 뒤 단계가 호출되지 않는지 확인할 수 있습니다. 서비스 입력으로 직접 비교하려면 별도 원천 ID·table·규칙 ID로 등록하고 원래 정상 원천을 유지합니다.

규칙 자체가 없는 경우, 조건표의 적용 행이 없는 경우, 감지가 끝났지만 경보가 없는 경우를 서로 다른 사례로 봅니다. 실패 뒤에는 예측·관계 반영의 성공 표시가 생기면 안 됩니다. 예외 메시지만 보고 불량이 없다고 해석하지 않습니다.""",
('pipeline',2): """**분석 기능과 입력을 함께 연결합니다.** 분류 화면만 있던 프로젝트에 PyOD와 Chronos 선택을 추가하도록 요청합니다. 의존성과 잠금 파일을 갱신한 뒤 `uv sync --frozen --extra models --extra dev`를 적용합니다. PyOD는 선택 LOT의 앞 구간을 기준으로 쓰고, Chronos는 config.yaml의 forecast_model을 사용합니다. 필요한 로컬 가중치가 없으면 준비 여부를 확인합니다. 서비스 답변용 API 모델을 켜는 설정과 이 CPU 분석은 별개입니다.

예측 매개변수 파일 forecast.json을 프로젝트 루트에 만듭니다. 합성 LOT4·쿠션22의 마지막20행을 남기는 첫 설정은 다음과 같습니다.

```json
{"column_id":22,"lot_id":"4","horizon":20,"evaluate_last":true}
```

화면에서 먼저 같은 설정의 결과를 읽고, 파이프라인에도 `uv run --env-file .env python scripts/reload.py --profile synthetic --source shots --rule cushion-relative --predict forecast --parameters forecast.json`으로 연결합니다. 참고 코드의 예측 입력 최소200개는 평가로 남긴20개를 제외한 뒤의 개수입니다. 원천 전체 행 수가 충분해도 선택 LOT가 짧으면 실행할 수 없습니다. 예측을 선택하지 않은 실행과 선택했지만 실패한 실행은 구분합니다.""",
('pipeline',3): """**평가할 행부터 맞춥니다.** 기본 PyOD는 앞200행 뒤를 평가하고 Chronos 예시는 마지막20행을 남깁니다. 이 두 출력 전체를 그대로 같은 분모라고 비교하지 않습니다. 합성 LOT가240행이면 마지막20행을 공통 관찰 구간으로 정하고, PyOD 기준220행/평가20행과 Chronos 과거220행/평가20행을 대조할 수 있습니다. 규칙은 자기 기준200행을 유지하되 비교표에는 공통 마지막20행에서의 관측만 따로 집계합니다. 학습/기준 구간의 차이도 표에 남깁니다.

원본 행 번호는 LOT 안의 상대 순서와 다를 수 있습니다. 점수 배열의 첫 항목이 원본 어느 행인지 연결하는 출력을 요청하고 실제 배열 길이를 대조합니다. 참고 PyOD 결과의 observations에는 원본 row_no·row_id·LOT·값·점수·예측이 함께 들어 있고 결과 표에서 볼 수 있습니다. 자기 구현도 점수·예측·평가 행의 길이를 확인하며 다르면 중단하도록 만듭니다. 실행 시간은 같은 요청의 trace에서 측정한 단계 시간을 사용하고, 측정하지 않은 모델은 미실행으로 남깁니다."""
}

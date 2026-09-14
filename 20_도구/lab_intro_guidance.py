"""First-day guidance at the action that needs it; no runtime claims."""
AFTER_ACTION = {
('intro',0): """**빈 폴더에서 첫 화면까지.** 코딩 에이전트에게 먼저 `AGENTS.md`와 `constitution.md`를 읽고 오늘의 표 적재·조회만 작은 순서로 만들도록 요청합니다. 전체 과정의 기능을 한 번에 만드는 요청으로 넓히지 않습니다. 화면은 Vue, 서버는 FastAPI, 표 저장은 PostgreSQL이라는 준비된 방향을 사용하되 코드 구조와 구현은 에이전트가 맡습니다. 첫 결과는 프로필·원천 선택, 파일 읽기, 행 수와 열 사전 보기입니다.

합성 자료를 선택했다면 `mapping.json`의 `profiles → synthetic → sources → shots`에서 경로가 `data/generated/shots.csv`인지 읽고 실제 파일을 엽니다. `conditions`와 `worklog`는 별도 원천입니다. 원본을 선택했다면 해당 원천의 실제 파일 경로와 존재 여부부터 확인합니다.

**만든 뒤 실행합니다.** 첫날 뼈대에는 아래 명령에 필요한 파일도 아직 없습니다. 에이전트가 `pyproject.toml`·`uv.lock`, `frontend/package.json`·잠금 파일, `scripts/bootstrap.py`·`scripts/serve.py`를 만들고 실행 순서를 README에 적었는지 먼저 확인합니다. 파일이 없으면 명령을 반복하지 말고 구현 요청의 빠진 연결로 되돌아갑니다.

1. `.env.example`을 로컬 `.env`로 복사합니다. 기존 파일은 덮지 않습니다. SERVICE_TOKEN은 자신이 정한 접속 값이고 모델 키와 다릅니다. 모델 호출은 아직 꺼 둡니다.
2. 설치 PDF에서 준비한 Docker를 켜고 프로젝트 루트 터미널에서 `npx supabase@2.117.0 start`를 실행합니다. `supabase/config.toml`이 없는 첫 설정에만 `npx supabase@2.117.0 init`을 먼저 합니다. 표시된 DB 주소를 DATABASE_URL에 넣고, 별도 읽기 전용 계정 주소를 READONLY_DATABASE_URL에 준비하도록 에이전트의 README와 대조합니다.
3. 아래는 참고 구조의 순서입니다. 자기 구현에서 명령을 바꿨다면 같은 역할을 하는 명령을 에이전트와 확인하고 README에 남깁니다.

```powershell
uv sync --frozen --extra dev
uv run --env-file .env python scripts/bootstrap.py
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
uv run --env-file .env python scripts/serve.py
```

`http://localhost:8000`을 열고 연결 칸에 자신의 SERVICE_TOKEN을 넣습니다. 서버 터미널은 켜 둡니다. 상태 응답을 본 뒤 합성 프로필의 shots를 적재해 표를 읽습니다. 모델이 꺼져 있어도 이 파일·표 단계는 확인할 수 있어야 합니다. 주소가 열리지 않으면 터미널의 첫 오류, 401이면 토큰, DB 오류면 저장소 상태와 bootstrap 결과부터 에이전트와 확인합니다.""",
('intro',1): """**지금 모델을 연결합니다.** 코드를 작성하는 에이전트와 이 서비스가 질문에 답할 때 호출하는 모델은 별개입니다. 수업에서 정한 모델의 이름·주소·키를 로컬 `.env`의 API_MODEL_NAME·API_MODEL_BASE_URL·API_MODEL_KEY에 넣습니다. 지원 응답 형식과 비용을 확인한 뒤에만 ALLOW_MODEL_CALLS=true로 켭니다. 값이 없는 예시 파일만으로 모델이 준비된 것은 아닙니다. 사내 모델을 쓰기로 했다면 별도 INTERNAL_MODEL 설정을 사용하며 API로 자동 우회하지 않습니다.

설정을 바꿨으면 서버 터미널에서 Ctrl+C로 종료한 뒤 같은 실행 명령으로 다시 시작합니다. 첫 질문 하나만 보내 SQL과 결과표를 봅니다. 연결이 실패하면 공급자·주소·모델 이름과 오류 이유를 확인하고, 성공한 다른 모델 결과로 바꾸어 표시하지 않습니다. 질문에는 키를 붙여 보내지 않습니다.

**작은 범위로 답을 확인합니다.** 질문이 가리킨 열과 LOT를 결과 SQL에서 찾고, 선택된 원본 행의 값과 계산을 대조합니다. 평균이면 어떤 행을 더해 몇 건으로 나눴는지, 상위 10개이면 어떤 열로 정렬했는지 확인합니다. 조건표나 작업일지가 필요한 질문은 해당 원천을 별도로 적재해야 합니다. 검사 라벨이 없는 표에서 불량 수를 지어내지 않습니다. 열 이름·뜻·단위의 힌트를 바꾸기 전 같은 질문의 입력과 결과를 남겨 다음 단계 비교에 씁니다.""",
('intro',3): """**관계표를 먼저 읽습니다.** 첫날 참고 구현은 `ontology/synthetic.csv`를 읽어 경로를 찾는 방식입니다. 이 단계에 Neo4j를 새로 띄울 필요는 없습니다. 행의 `source`·`relation`·`target`·`provenance`가 각각 출발 ID·관계·도착 ID·근거입니다. 화면에서 관계표를 읽은 뒤 `synthetic:shots:lot:4`에서 `synthetic:worklog:lot:4`로 가는 경로를 확인합니다. 두 ID는 오늘 제공된 합성 관계표에서 읽은 예시입니다.

새 관계는 실제 자료에서 근거를 확인한 경우에만 추가합니다. 이미 있는 행을 그대로 복제하지 말고 자기 질문에 필요한 연결을 고릅니다. 확인할 관계가 더 없으면 기존 경로의 뜻을 설명하는 데서 멈추어도 됩니다. CSV를 고쳤다면 화면의 관계표 읽기를 다시 요청하고 같은 두 ID로 변경을 확인합니다. 나중에 그래프 DB로 옮기는 것과 오늘 관계의 뜻을 확인하는 일은 구분합니다."""
}

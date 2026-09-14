# 설비 이상 대응 어시스턴트

학생이 만드는 서비스의 참고 완성본입니다. Vue 화면에서 자료의 뜻을 확인하고, FastAPI가 표·그래프·문서·모델·승인 기록을 연결합니다. 코드와 설정은 새로 작성했습니다. 교육용 합성 자료는 KAMP 원본과 별도 프로필입니다.

## 시작 전

Python 3.12, uv, Node 22.18 이상, Docker Desktop이 필요합니다. 기존 네 개 설치 PDF를 마친 뒤 이 순서로 연결합니다. 이 완성본은 설치·모델·학생 실습을 끝까지 실행한 결과물이 아닙니다. 확인 범위는 강사용 검증 기록에 있습니다.

1. 이 폴더를 VS Code로 열고 `.env.example`을 **새 `.env`**로 복사합니다. 기존 `.env`는 덮지 않습니다.
2. `.env`에 서비스 토큰과 서로 다른 사람 승인 토큰을 정합니다. 모델 이름·주소·키는 사용할 계정의 실제 값을 입력합니다. 추정한 모델명이나 다른 공급자로 자동 전환하는 설정은 없습니다.
3. 터미널에서 `npx supabase@2.117.0 init`을 한 번 실행합니다. 이미 `supabase/config.toml`이 있으면 init은 생략합니다. `npx supabase@2.117.0 start`로 로컬 DB를 시작합니다. 기존 migrations는 보존합니다.
4. Supabase가 표시한 로컬 Postgres 연결 주소를 DATABASE_URL에 넣습니다. 같은 호스트·포트·DB를 사용하는 **lab_reader** 계정 주소를 READONLY_DATABASE_URL에 넣고 별도의 암호를 정합니다. `bootstrap.py`가 이 계정을 생성합니다. 비밀값을 가이드나 저장소에 쓰지 않습니다.
5. `.env`의 NEO4J_PASSWORD를 설정하고 `docker compose up -d graph`를 실행합니다. 이 컨테이너는 그래프용이며 표·벡터는 Supabase에 남습니다.

## 설치와 서버

아래 명령은 이 폴더의 터미널에서 순서대로 실행합니다. 앞 명령이 실패하면 다음으로 넘어가지 말고 첫 오류를 확인합니다.

```powershell
uv sync --frozen --extra dev
uv run --env-file .env python scripts/bootstrap.py
uv run --env-file .env python scripts/seed_rules.py
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
uv run --env-file .env python scripts/serve.py
```

브라우저에서 `http://localhost:8000`을 엽니다. 설정에 서비스 토큰을 입력하고 연결 확인을 누릅니다. `/health`의 server/database는 해당 연결만 확인합니다. 모델이 꺼져 있어도 표 적재·통계·규칙 계산은 가능합니다. 모델 질문 버튼은 꺼진 이유를 표시합니다.

개발 중 화면 변경을 바로 보려면 frontend 폴더에서 `npm.cmd run dev`를 별도 터미널에 띄우고 `http://localhost:5173`을 엽니다. 백엔드·MCP는 serve.py가 실행합니다. 서버 종료는 해당 터미널의 Ctrl+C입니다.

## 자료를 선택하는 순서

`synthetic`: 제공한 1,440행·6 LOT 샷, 조건표, 작업일지와 규칙 라벨 분류표입니다. 실제 설비에서 측정한 값이 아닙니다. 화면에서 자료를 고르고 표 사전을 읽은 다음 원천별로 적재합니다. 기본 원천 ID는 shots, conditions, worklog, labeled입니다.

`kamp`: 직접 확보한 원본 파일을 mapping.json에 연결합니다. 제공 ZIP에는 원시 측정 CSV가 없었습니다. 경로만 있다는 이유로 원본 실습 준비가 끝난 것은 아닙니다. `scripts/data_check.py`로 헤더·경로·기능 전제를 확인합니다. 없는 파일을 합성 파일로 자동 대체하지 않습니다.

`transfer`: 도서 목록과 대출 기록, 도서관 규정 3장입니다. 원천은 books 또는 loans입니다. 제조용 LOT·쿠션 규칙이 이 주제에서도 타당한지 학생이 바꾸는 재료입니다. 가상의 ID만 사용했습니다.

## 실습 단계별 추가 설치

표 분류·PyOD·Chronos·열화상은 `uv sync --frozen --extra models --extra dev`가 필요합니다. CPU 학습은 버튼을 누르거나 model_job.py를 실행할 때만 시작됩니다. 큰 모델의 준비 시간과 메모리는 별도 확인 대상입니다.

문서 검색은 `uv sync --frozen --extra documents --extra dev` 후, 공개 임베딩·리랭커 파일을 내려받을 준비 단계에서만 `.env`의 ALLOW_MODEL_DOWNLOADS를 true로 바꾸고 `uv run --env-file .env python scripts/cache_models.py`를 실행합니다. 준비 후 false로 되돌립니다. 기본 Markdown 30장은 Docling 모델이 필요 없고, PDF 변환을 선택하면 Docling의 로컬 모델 경로도 준비해야 합니다.

질문 응답은 공급자가 JSON schema 응답을 지원하는지 확인하고 ALLOW_MODEL_CALLS=true로 선택한 뒤 시작합니다. `api`와 `internal`은 서비스에서 쓰는 모델 경로입니다. VS Code의 코딩 에이전트 모델과 별개입니다. 가격이 미설정이면 비용을 0으로 만들지 않고 미측정으로 표시합니다.

평가는 `uv sync --frozen --extra documents --extra evaluation --extra dev`로 설치합니다. 같은 기능을 유지할 때 extras를 합쳐 지정하세요. uv sync는 선택하지 않은 extra의 패키지를 제거할 수 있습니다. 모델 분석까지 모두 필요하면 네 extra를 함께 지정합니다.

## 읽어야 할 결과

응답의 status와 reason을 먼저 읽고, answer와 evidence를 대조합니다. none은 조회 결과 없음, insufficient는 판단 조건 부족, refused는 답변·실행 거절입니다. 모두 정상 설비라는 뜻이 아닙니다. failed는 실행·심사 실패, error는 잘못된 입력·설정입니다. pending_approval은 사람 결정 대기입니다.

SQL은 읽기 전용 계정·구문 검사·행 상한을 거칩니다. 모델 심사는 대상·범위·계산·의미를 나눕니다. 심사 점수는 실제 정답을 보증하지 않습니다. 결과표와 질문을 직접 대조하는 자리가 남습니다.

원인 후보와 고장 확정은 다릅니다. RAG는 현행 문서만 인용하고, 관계 경로는 연결 근거를 보여 줍니다. 예측값이 임계를 넘는 샷 순서는 실제 고장 수명으로 바꾸지 않습니다. 사람 승인은 기록된 제안의 버전·해시에만 적용됩니다.

## 구조

- backend/data: CSV·열 사전·SQL·품질·시각화 입력
- backend/ontology: Neo4j 관계와 경로, Postgres outbox 반영
- backend/detect: 규칙·표 분류·PyOD·Chronos·비전
- backend/rag, eval, report: 문서 근거·평가·출처가 있는 보고서
- backend/process, agent: 승인·결정 기록과 중단 가능한 순서
- backend/common: 설정·응답·관측·모델 호출 경계
- mcp_server: 다섯 업무 도구
- .agent/skills: 제공한 spec/debug. 학생이 만드는 추가 스킬은 일차별 가이드에서 다룹니다.

## 간단 검사와 배포

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:RAGAS_DO_NOT_TRACK='true'
$env:DEEPEVAL_TELEMETRY_OPT_OUT='YES'
uv run --no-sync python -m pytest -q
```

이 검사는 모델·DB·실습 완주를 대신하지 않습니다. 배포의 준비와 실행 순서는 `배포.md`에 있습니다. deploy 스크립트는 자동으로 호출되지 않습니다. 실습은 각 일차 가이드에서 오늘 범위만 진행합니다.

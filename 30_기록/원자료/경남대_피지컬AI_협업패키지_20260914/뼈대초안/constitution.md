# constitution — 설비 이상 대응 어시스턴트

이 문서는 이 서비스가 무엇이고 무엇을 약속하는지 정한다. 구현이 이 문서와 어긋나면 구현이 틀린 것이다. 작업 방식은 `AGENTS.md`가 정한다.

## 1. 정체
설비의 공정 데이터·검사 기록·사내 문서를 한 서비스에서 읽고, 이상을 감지하고, 문서에서 근거를 찾아 원인을 설명하고, 조치를 제안하며, 사람이 승인한 조치만 기록·실행한다.

다섯 원칙.
1. 데이터는 그 뜻과 함께 다룬다 — 열 이름·단위·정상 범위는 `mapping.json`에 있고, 코드는 그것을 읽는다.
2. 의미는 온톨로지에 심는다 — 무엇이 무엇과 어느 키로 이어지는지는 `ontology/ontology.csv`가 정하고, 그래프는 그 표를 따른다.
3. 근거 없이 답하지 않는다 — 문서·표·그래프 중 확보된 근거만 결합해 답하고, 없으면 거절한다.
4. 도구는 한 곳에서 — 에이전트가 쓰는 도구는 `mcp_server/` 하나에 있고, 같은 계약으로 호출된다.
5. 판단은 사람이 한다 — 상태를 바꾸는 조치는 승인 없이 실행되지 않는다.

## 2. 층
`data → ontology → detect → rag → tools → agent → process → ui`. 아래층은 위층을 모른다. 층을 건너뛰는 호출은 없다. 층 이름은 폴더 이름이고 로그의 `layer` 값이다. 각 층은 `gateway.py`(밖으로 나가는 모든 호출)와 `service.py`(층의 일)를 가진다.

## 3. 주소와 응답
- 백엔드 `http://localhost:8000`, 프론트 `http://localhost:5173`. 변경은 `config.yaml`.
- API 경로: `/health` · `/trace/{rid}` · `/api/data/upload` · `/api/data/query` · `/api/data/catalog` · `/api/data/series` · `/api/data/quality` · `/api/report` · `/api/ontology/load` · `/api/ontology/path` · `/api/detect/rules` · `/api/detect/alarms` · `/api/detect/events` · `/api/detect/models` · `/api/rag/ask` · `/api/rag/docs` · `/api/eval/run` · `/api/agent/run` · `/api/agent/resume` · `/api/approvals` · `/api/approvals/{id}/decide`.
- 모든 응답은 한 형식이다.
```
{"rid":"…","status":"ok|none|refused|failed|error|pending_approval|insufficient",
 "answer":…, "evidence":[…], "reason":"…(status≠ok일 때 필수)",
 "meta":{"model":"…(모델을 썼을 때)","tokens_in":n,"tokens_out":n,"warnings":[…(폴백·저품질 경로를 탔을 때)]}}
```
- 응답 JSON은 `backend/common/response.py` 한 곳에서만 만든다.
- 흘러나오는 순서: 답 → 근거 → 상태.

## 4. 근거 형식 (evidence 항목)
- 문서: `{"kind":"doc","ref":"[문서번호 §조항] 파일명","quote":"…","status":"current|obsolete"}`
- 표: `{"kind":"table","ref":"[표] 테이블·행 조건","sql":"…","rows":n}`
- 경로: `{"kind":"path","ref":"[경로] 노드 → 노드 → 노드","hops":n}`
근거 없는 문장은 `answer`에 들어가지 않는다.

## 5. 상태 값의 뜻
`ok` 근거 있는 답 · `none` 조회했으나 결과 없음(정상) · `refused` 근거가 없어 답하지 않음 · `insufficient` 입력이 부족해 판단 불가(부족한 것을 `reason`에) · `failed` 수행 실패(SQL 오류 등, 지어내지 않음) · `error` 계약 위반·잘못된 인자 · `pending_approval` 사람 승인 대기.
`none`을 `ok`로, `failed`를 `none`으로 바꾸어 돌려주지 않는다.

## 6. 설정
- `mapping.json`: 설비·제품·파일 경로·시간열·샷/LOT열·채널(뜻·단위·정상범위·출처)·라벨열·검사 파일·공차·문서 목록·이미지 폴더·역할 이름.
- `config.yaml`: 주소·청킹 크기·겹침·상위 k·리랭커 후보 수·걸음 상한·자율성 기본 레벨·**모델 목록(둘 이상, 기본 하나)**·행 제한.
- 코드에 위 값을 리터럴로 쓰지 않는다. 데이터 파일을 복사·이동하지 않는다.

## 7. 저장
- 원본 데이터: Supabase(Postgres) 테이블. 표 설계는 마이그레이션 파일로. 업로드는 같은 파일을 두 번 넣지 않는다(파일 해시).
- 모델이 만든 SQL은 실행 전 파싱 검사(SELECT만·깊이·허용 표)를 거치고, 읽기 전용 계정으로, 실행 계층이 행을 제한한다. SQL 본문을 바꾸지 않는다.
- 벡터: pgvector. 그래프: 그래프DB(`ontology/ontology.csv`가 정한 것만).
- 서비스가 만든 기록(알람·이벤트·제안·승인·평가): Postgres. 그래프에는 노드로도 남긴다.

## 8. 관측
- 로그는 `logs/app.jsonl` 한 파일, 한 줄 JSON, 필드 고정: `ts rid layer step in out ms status loc [reason] [model tokens_in tokens_out]`(모델 호출 줄).
- `rid`는 요청당 하나이며 화면 → 백엔드 → 저장소 → 모델까지 그대로 전달된다.
- `layer`·`step`은 `AGENTS.md`의 목록에서만 쓴다. `loc`은 `파일:함수`. `in`·`out`은 길이·개수·선택된 ID 같은 요약만. 본문·임베딩·전체 문서는 남기지 않는다.
- 로그는 게이트웨이가 남긴다. `print`와 임시 로그는 없다.
- `/health`는 층별 상태와 전제 라우트 목록을, `/trace/{rid}`는 그 요청의 로그 줄들을 돌려준다.

## 9. 불변 조건
- 모든 단계는 입력 조건과 출력 조건을 가지며 `.agent/invariants.md`에 적혀 있다. 조건이 깨지면 그 단계는 `failed`로 끝나고 다음 단계는 실행되지 않는다.
- `rag.answer`는 근거 0개로 호출되지 않는다. 상태가 `obsolete`인 문서는 근거가 되지 않는다.
- 도구는 빈 결과를 `none`으로, 잘못된 인자를 `error`로 돌려준다. 예외를 삼키지 않는다.
- `record_decision`은 `pending_approval`을 거친 항목에만 호출된다.
- 도구가 `none`을 돌려주면 에이전트는 그것을 「정상」으로 읽지 않고 `insufficient`로 멈춘다.
- 후속 질문은 직전 요청의 상태(SQL·필터·근거)를 받되, 그 상태에서 표·열을 지어내지 않는다.

## 10. 금지
데이터 복사·이동 · 조용한 실패(빈 값·기본값·재시도로 오류 숨김) · **조용한 폴백**(낮은 품질 경로로 내려갔으면 `meta.warnings`에 반드시 남긴다; 사내 모델 실패를 API로 말없이 넘기지 않는다) · 승인 우회 · 층 섞기 · 게이트웨이 밖 외부 호출 · 값·경로·이름 리터럴 · 옛 경로를 살려 두는 우회·플래그·별칭 · 증상 자리에 조건문으로 덮기 · 재현 없는 수정 · 특정 샘플(파일명·번호·값)에 맞춘 로직 · 비밀·개인정보를 코드·로그·커밋에 남기기.

## 11. 화면
업로드 · 질문(우리말 → SQL, 실행 SQL·체크리스트 O/X/모름·점수 표시) · 문서 질문(답·근거 세 갈래·상태) · 채점표 · 알람 목록 · 이상 이벤트 · 승인 대기(목록·승인/반려·사유) · 관측(요청별 trace·모델·토큰·비용). 답마다 어느 모델이 답했는지 보인다. 같은 뜻은 같은 색·용어·정렬.

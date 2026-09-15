# 개인 PC 실행 준비 — 제작 중

코딩 에이전트가 수행할 환경 작업이다. 학생에게 명령 암기를 요구하지 않는다. 현재 Compose 정적 확인 대상이며 전체 컨테이너 구동 검증은 미완료다. 학생 공개용 설치 문서가 아니다.

`compose.local.yml`은 개인 PC용 독립 구성이다. 원천 compose와 합치지 않는다. 포트 충돌을 먼저 확인하고 다른 작업을 종료하거나 볼륨을 삭제하지 않는다.

1. Docker Desktop의 Linux 컨테이너 엔진 실행을 확인한다.
2. 이 폴더에서 `docker compose -f compose.local.yml up -d --build`로 시작한다.
3. 그래프가 준비된 뒤 `docker compose -f compose.local.yml exec hydops-api python -c "from hydops.b4_ontology import graph; print(graph.seed_graph())"`로 교육용 기준 관계를 준비한다. 초기 준비용이며 학생 수정 후 반복 실행하지 않는다.
4. `docker compose -f compose.local.yml exec hydops-api python -c "from hydops.b6_sop import search; print(search.index_sections())"`로 오프라인 검색 인덱스를 준비한다.
5. 첫 관찰은 `http://localhost:8800`, 콘솔은 `http://localhost:8910/console/`에서 한다. 사이트 접근 성공과 데이터/업무 정상 동작은 별도로 확인한다.
6. 플랫폼 연결 단계에서 `docker compose -f compose.local.yml exec hydops-api python scripts/bootstrap_platform.py --all`을 실행한다. 기존 정의를 다시 가져오므로 학생별 변경이 생긴 뒤 반복 실행하지 않는다. Watch는 자동 활성화하지 않는다.
7. 수업 종료는 `docker compose -f compose.local.yml stop`, 재개는 `docker compose -f compose.local.yml start`다. `down -v`는 학습 데이터를 지우므로 복구 지시로 쓰지 않는다.

현재 구성은 비용 없는 준비 확인을 위해 offline으로 고정한다. offline은 실제 LLM이 아니다. 플랫폼의 업무 에이전트 실행은 별도 LLM 경로가 있으므로 Watch 활성화·업무 시작은 아직 하지 않는다. 모델 중계 설정·호환성을 준비한 다음 학생용 모델 호출 절차를 추가해야 한다. 이 파일에는 비밀키를 기록하지 않는다.

원천의 일부 실습이 쓰는 600MB 이상의 raw 데이터는 복제하지 않았다. 첫날 작은 실제 표본과 기존 reduced 데이터를 제공하고, 후반 실제 raw 전체가 필요한 활동은 입력·크기를 별도로 안내한다. 이 상태로 원천의 모든 테스트/명령이 그대로 동작한다고 가정하지 않는다.

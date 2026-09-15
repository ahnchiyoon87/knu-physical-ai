# 개인 PC 실행 준비 — 제작 중

코딩 에이전트가 수행할 환경 작업이다. 학생에게 명령 암기를 요구하지 않는다. 현재 제작 PC에서 로컬 네 서비스 기동과 첫날 데이터 처리를 확인했다. 새 학생 PC의 설치 완주와 중앙 모델 중계 연결은 별도 확인 대상이다. 학생 공개용 최종 설치 문서가 아니다.

`compose.local.yml`은 개인 PC용 독립 구성이다. 원천 compose와 합치지 않는다. 포트 충돌을 먼저 확인하고 다른 작업을 종료하거나 볼륨을 삭제하지 않는다.

1. Docker Desktop의 Linux 컨테이너 엔진 실행을 확인한다.
2. 일반 빌드는 이 폴더에서 `docker compose -f compose.local.yml up -d --build`로 시작한다. Windows에서 한글 경로의 빌드 전달 문제가 발생하면 프로젝트 루트에서 `python 제작도구/로컬이미지_빌드.py`로 이미지를 먼저 만들고, 이 폴더에서 `docker compose -f compose.local.yml up -d --no-build`로 시작한다. 후자가 현재 제작 PC에서 확인한 경로다.
3. 그래프가 준비된 뒤 `docker compose -f compose.local.yml exec hydops-api python -c "from hydops.b4_ontology import graph; print(graph.seed_graph())"`로 교육용 기준 관계를 준비한다. 초기 준비용이며 학생 수정 후 반복 실행하지 않는다.
4. `docker compose -f compose.local.yml exec hydops-api python -c "from hydops.b6_sop import search; print(search.index_sections())"`로 오프라인 검색 인덱스를 준비한다.
5. 첫 관찰은 `http://localhost:8800`, 콘솔은 `http://localhost:8910/console/`에서 한다. 사이트 접근 성공과 데이터/업무 정상 동작은 별도로 확인한다.
6. 플랫폼 연결 단계에서 `docker compose -f compose.local.yml exec hydops-api python scripts/bootstrap_platform.py --all`을 실행한다. 기존 정의를 다시 가져오므로 학생별 변경이 생긴 뒤 반복 실행하지 않는다. Watch는 자동 활성화하지 않는다.
7. 수업 종료는 `docker compose -f compose.local.yml stop`, 재개는 `docker compose -f compose.local.yml start`다. `down -v`는 학습 데이터를 지우므로 복구 지시로 쓰지 않는다.

현재 구성은 비용 없는 준비 확인을 위해 offline으로 고정한다. offline은 실제 LLM이 아니다. 플랫폼의 업무 에이전트 실행은 별도 LLM 경로가 있으므로 Watch 활성화·업무 시작은 아직 하지 않는다. 모델 중계 설정·호환성을 준비한 다음 학생용 모델 호출 절차를 추가해야 한다. 이 파일에는 비밀키를 기록하지 않는다.

첫날에 사용하는 원본 `data/raw/TS1.txt`, `PS1.txt`, `FS1.txt`와 `profile.txt`, 데이터 설명 파일을 포함한다. PS1은 약91.4MB이며 원본의 다른 센서 파일 전체를 포함한 것은 아니다. 기존 `data/reduced`도 제공한다. 원본 경로를 찾지 못하면 임의 데이터로 대체하지 않는다.

## 첫날 개인 작업 준비

프로젝트 루트에서 에이전트가 `python 제작도구/첫날_작업본준비.py practical student-work/첫날-실전` 또는 `python 제작도구/첫날_작업본준비.py integrated student-work/첫날-통합`을 실행한다. 준비 도구는 원본을 복사하고 플랫폼 경로만 맞추며 과제 정답은 채우지 않는다. 이미 존재하는 작업 폴더는 덮어쓰지 않는다.

노트북 실행 패키지와 한글 글꼴은 프로젝트 루트에서 `python 제작도구/로컬이미지_빌드.py --notebook`으로 준비한다. 코드 검사는 `제작도구/첫날_컨테이너검사.py --help`의 작업 폴더·기록 경로를 지정해 실행하며 통합반은 `--notebook`을 쓴다. 이 도구의 테스트 결과와 학생이 화면에서 결과를 읽고 판단하는 활동은 구분한다.

노트북을 여는 UI와 커널 연결은 사용하는 코딩 도구에 맞춰 준비한다. 제작 캡처는 별도 JupyterLab에서 실제 실행한 결과이며 학생의 기본 UI를 JupyterLab으로 확정한 것은 아니다. 토큰·키를 가이드나 Git에 기록하지 않는다.

# 중앙 중계 운영 도구

이 폴더는 강사용 배포·검사 도구다. 학생에게 배포하는 실습가이드가 아니다.

## 현재 구성

Cloud Run `knu-litellm` → Cloud SQL `knu-litellm-db`와 외부 모델 제공사. 프로젝트는 `project-f49d373f-f76d-47a1-bdb`, 리전은 `asia-northeast3`다. Secret Manager에 관리키·암호화키·DB 연결을 보관한다. 모델 제공사 연결은 아직 비어 있다. GCP 로그인만으로 OpenAI API 인증이 되지는 않는다.

초기 시험 구성은 Cloud Run 최소0/최대1, CPU1/2Gi, 동시요청20, 요청제한600초와 DB db-f1-micro/SSD10GB다. 학생60명 동시 사용을 검증한 사양이 아니다. PostgreSQL·이미지 저장 등의 비용은 Cloud Run 최소0이어도 별도로 발생한다.

## 실행 순서

1. `비밀값준비.py`: 없는 비밀값을 생성한다. 기존 활성 버전은 재발급하지 않는다. 특히 salt-key를 임의 변경하지 않는다.
2. `DB연결준비.py`: 준비된 전용 DB에 사용자/DB를 만들고 연결 문자열을 Secret Manager에 보관한다.
3. `cloudbuild.yaml`: Dockerfile/config.yaml 두 파일로 이미지를 빌드한다. 프로젝트 전체를 빌드 소스로 업로드하지 않는다.
4. `배포.ps1`: 고정 digest의 이미지를 배포한다. 최초 빈 DB 초기화 때만 `-InitializeSchema`를 사용한다. 일반 배포는 스키마 변경을 끈다. LiteLLM 버전 업그레이드는 별도 마이그레이션·백업·검증 계획이 필요하다.
5. `중계접속확인.py`: 인증 거부, 관리키, 모델 목록과 health 확인. 추론 호출 없음.
6. `가상키확인.py`: 만료1시간 시험키 생성, 예산0 차단, 관리 권한 차이, 새 revision에서 키 유지, 폐기 후 차단 확인. 실제 Cloud Run revision을 새로 생성한다. 시험키는 마무리 시 폐기하며 추론 요청을 보내지 않는다.

PowerShell의 gcloud.ps1 실행 정책 오류는 `gcloud.cmd`로 우회한다. 시스템 보안 정책을 변경하지 않는다. 배포 스크립트는 `powershell -NoProfile -ExecutionPolicy Bypass -File 제작도구/중앙중계/배포.ps1`로 해당 프로세스에서 실행할 수 있다.

## 학생 연결 전 남은 일

- 제공사 API 키를 Secret Manager에 연결하고 `coding` 별칭을 `openai/gpt-5.6-luna`로 등록. 공식 ID는 확인했지만 계정 권한·중계 동작은 미확인이다.
- 코딩 에이전트의 일반 응답·스트리밍·도구 호출, 오류/429와 한도, 학생별 기록을 실제로 확인.
- 학생용 API 키 인증과 관리자 접근 정책을 확인한 뒤 학생 접근 주소를 열기. 현재 서비스는 GCP IAM 인증도 필요하다.
- 여러 인스턴스로 확장하려면 Redis를 포함한 제한·사용량 집계 공유를 설계/검증. 지금 설정으로60명 운영을 확정하지 않는다.
- 별도 설치 안내와 실제 화면 캡처, 사용자 실습·비용 기록을 연결.

검사 결과는 `작업기록/LiteLLM설정_20260915`를 따른다. 키 값과 인증 토큰은 터미널·Git·대화·화면 캡처에 넣지 않는다.

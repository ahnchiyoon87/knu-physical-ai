# 실09-start

이전 단계 코드가 들어 있습니다. 오늘 기능은 일차 가이드를 읽으며 추가합니다. 기본 실행은 uv sync --frozen --extra dev → uv run --env-file .env python scripts/bootstrap.py → npm.cmd --prefix frontend ci → npm.cmd --prefix frontend run build → uv run --env-file .env python scripts/serve.py 순서입니다. 필요한 models/documents/evaluation extra와 DB 준비는 실행 연결 안내에서 이어집니다.

이전 단계 기능: agent, data, eval, forecast, judge, models, pipeline, pyod, quality, rag, rules, visual

자기 폴더는 보존하고 새 폴더에서 합류하세요. .env.example은 빈 설정 예시입니다. 실제 키는 넣지 않았습니다. 기본 합성 자료는 원본 측정 파일이 아닙니다.

코드·구문·구성 검토와 실제 학생 완주는 별개입니다. 모델과 DB를 끝까지 실행한 확인본으로 표현하지 않습니다.

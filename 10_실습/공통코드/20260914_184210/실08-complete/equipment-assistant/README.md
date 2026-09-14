# 실08-complete · 두 반 공통 실습

오늘까지의 참고 완성 코드입니다. 자기 결과와 비교할 수 있으며 화면이나 코드가 같을 필요는 없습니다.

기본 실행 순서: `uv sync --frozen --extra dev` → `.env.example`을 참고해 자기 `.env` 준비 → `uv run --env-file .env python scripts/bootstrap.py` → `npm.cmd --prefix frontend ci` → `npm.cmd --prefix frontend run build` → `uv run --env-file .env python scripts/serve.py`. 필요한 모델·문서·평가 extra와 DB 준비는 실행 연결 안내를 따릅니다.

자기 프로젝트는 보존하고 새 폴더에서 엽니다. 실제 키와 원시 측정 자료는 포함하지 않습니다. synthetic은 교육용 합성입니다.

포함 기능: data, deploy, eval, forecast, integration, judge, models, pipeline, pyod, quality, rag, rul, rules, table, vision, visual

모델·DB를 자동으로 실행하지 않습니다. 실제 실행에 필요한 원천·계정·허용한 모델과 비용을 확인합니다.

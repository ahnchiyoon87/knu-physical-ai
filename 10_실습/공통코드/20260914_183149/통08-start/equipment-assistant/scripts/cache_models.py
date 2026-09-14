"""Explicitly cache public embedding/reranker weights. No LLM inference."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if os.getenv('ALLOW_MODEL_DOWNLOADS','false').lower()!='true':
    raise SystemExit('ALLOW_MODEL_DOWNLOADS=true인 준비 단계에서만 실행합니다')
from backend.rag.gateway import encoder,reranker
encoder()
reranker()
print('문서 검색용 모델 파일 준비 완료. 질문 응답 모델은 호출하지 않았습니다.')

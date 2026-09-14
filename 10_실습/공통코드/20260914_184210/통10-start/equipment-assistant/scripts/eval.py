"""Run selected evaluation work only when explicitly requested by the operator."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import asyncio
import json
import os
from uuid import uuid4

from backend.common.config import configured_path
from backend.common.log import request_id
from backend.eval.service import run,validate_cases


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--profile",required=True)
    parser.add_argument("--provider",choices=["api","internal"],required=True)
    parser.add_argument("--questions",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--ragas",action="store_true")
    parser.add_argument("--confirm-model-calls",action="store_true")
    args=parser.parse_args()
    if not args.confirm_model_calls or os.getenv("ALLOW_MODEL_CALLS","false").lower()!="true":
        raise ValueError("선택한 질문셋의 모델 호출을 명시적으로 켜야 합니다")
    path=configured_path(args.output)
    if path.exists():
        raise ValueError("기존 평가 파일을 덮지 않습니다. 새 출력 이름을 선택하세요")
    cases=json.loads(configured_path(args.questions).read_text(encoding="utf-8"))
    validate_cases(cases,require_reference=args.ragas)
    rid=str(uuid4())
    token=request_id.set(rid)
    try:
        result=run(rid,args.profile,args.provider,cases).model_dump(mode="json")
        from backend.eval.regression import regression
        by_id={case["id"]:case for case in cases}
        for row in result["answer"]["results"]:
            case=by_id[row["case_id"]]
            row["regression"]=regression(case,row["result"])
            if args.ragas:
                from backend.eval.ragas_gateway import evaluate_sample
                response=row["result"]
                if response["status"]=="ok":
                    row["ragas"]=asyncio.run(evaluate_sample(args.provider,case["question"],
                        "\n".join(claim["text"] for claim in response["answer"]),
                        [e["quote"] for e in response["evidence"] if e["kind"]=="doc"],case.get("reference","")))
                else:
                    row["ragas"]={"status":"not_applicable","reason":"답변 없는 사례는 상태 계약으로 평가"}
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        sys.stdout.write(f"평가 결과 저장: {path.name}\n")
    finally:
        request_id.reset(token)


if __name__=="__main__":
    main()

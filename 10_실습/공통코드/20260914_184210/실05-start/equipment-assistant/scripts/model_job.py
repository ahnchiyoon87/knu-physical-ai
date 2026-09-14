"""Execute a named CPU model job with explicit parameters and retain its result."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import json
from uuid import uuid4

from backend.common.config import configured_path
from backend.common.log import request_id


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--job",required=True,help="분석 입력 JSON의 경로")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    output=configured_path(args.output)
    if output.exists():
        raise ValueError("기존 결과를 덮지 않습니다")
    inputs=json.loads(configured_path(args.job).read_text(encoding="utf-8"))
    token=request_id.set(str(uuid4()))
    try:
        if inputs["method"]=="vision":
            from backend.detect.vision_gateway import run
            result=run(**inputs["parameters"])
        else:
            from backend.detect.model_gateway import job
            result=job(**inputs)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        sys.stdout.write(f"분석 결과 저장: {output.name}\n")
    finally:
        request_id.reset(token)


if __name__=="__main__":
    main()

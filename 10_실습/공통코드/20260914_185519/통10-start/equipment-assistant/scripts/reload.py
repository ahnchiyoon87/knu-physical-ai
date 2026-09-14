"""Run the explicit ingest → rule detection → graph projection pipeline."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import json
from uuid import uuid4

from backend.common.log import request_id
from backend.agent.pipeline import run


def reload(profile: str, source_id: str, rule_id: str, prediction_request=None):
    rid=str(uuid4())
    token=request_id.set(rid)
    try:
        return run(rid,profile,source_id,rule_id,prediction_request)
    finally:
        request_id.reset(token)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--profile",required=True)
    parser.add_argument("--source",required=True)
    parser.add_argument("--rule",required=True)
    parser.add_argument("--predict",choices=["forecast","threshold","pyod","table"])
    parser.add_argument("--parameters",help="선택한 분석의 JSON 매개변수 파일")
    args=parser.parse_args()
    if bool(args.predict)!=bool(args.parameters):parser.error('--predict와 --parameters를 함께 지정하세요')
    prediction={'method':args.predict,'parameters':json.loads(Path(args.parameters).read_text(encoding='utf-8'))} if args.predict else None
    result=reload(args.profile,args.source,args.rule,prediction)
    sys.stdout.write(json.dumps(result,ensure_ascii=False,indent=2,default=str)+"\n")
    raise SystemExit(0 if result["status"]=="ok" else 1)


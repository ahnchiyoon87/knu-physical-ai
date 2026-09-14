"""Check configured data prerequisites without ingesting data or calling any model."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import csv
import json

from backend.common.config import configured_path, mapping

BLOCKS={
    "data":{"sources":["shots"],"documents":False,"labels":False},
    "quality":{"sources":["shots","labeled"],"documents":False,"labels":False},
    "table_model":{"sources":["labeled"],"documents":False,"labels":True},
    "rules":{"sources":["shots","conditions"],"documents":False,"labels":False},
    "rag":{"sources":["shots"],"documents":True,"labels":False},
    "agent":{"sources":["shots"],"documents":True,"labels":False}}


def inspect(profile: str,block: str,source_ids=None):
    if block not in BLOCKS or profile not in mapping()["profiles"]:
        raise ValueError("알 수 없는 프로필 또는 검사 블록입니다")
    requirement=BLOCKS[block]
    config=mapping()["profiles"][profile]
    checks=[]
    selected=source_ids or (list(config['sources']) if profile=='transfer' else requirement['sources'])
    for identity in selected:
        source=config["sources"].get(identity)
        if source is None:
            checks.append({"source":identity,"status":"missing","reason":"원천 매핑 없음"})
            continue
        path=configured_path(source["path"])
        if not path.is_file():
            checks.append({"source":identity,"status":"missing","reason":"원천 파일 없음"})
            continue
        with path.open(encoding=source.get("encoding","utf-8-sig"),newline="") as stream:
            reader=csv.DictReader(stream)
            missing={column["name"] for column in source["columns"]}-set(reader.fieldnames or [])
            first=next(reader,None)
        label_ok=not requirement["labels"] or bool(source.get("label_column_id"))
        passed=not missing and first is not None and label_ok
        checks.append({"source":identity,"status":"ready" if passed else "insufficient",
                       "missing_columns":sorted(missing),"has_rows":first is not None,"label_mapping":label_ok,
                       "time_axis":source.get("time_column") or "시각 열 없음",
                       "provenance":source["provenance"]})
    if requirement["documents"]:
        docs=config.get("documents",[])
        missing=[doc["id"] for doc in docs if not configured_path(doc["path"]).is_file()]
        checks.append({"source":"documents","status":"ready" if docs and not missing else "missing",
                       "missing":missing,"count":len(docs)})
    ready=all(check["status"]=="ready" for check in checks)
    return {"profile":profile,"block":block,"ready":ready,"checks":checks,
            "scope":"파일·머리글·첫 행·설정의 확인. 값 전체 검증이나 실습 실행 아님"}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--profile",required=True)
    parser.add_argument("--block",choices=list(BLOCKS),required=True)
    parser.add_argument('--sources',nargs='+',help='다른 주제에서 실제 선택할 원천 ID')
    args=parser.parse_args()
    result=inspect(args.profile,args.block,args.sources)
    sys.stdout.write(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    raise SystemExit(0 if result["ready"] else 1)

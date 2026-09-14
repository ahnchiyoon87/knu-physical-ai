"""Check current common packages without model/DB execution or student rehearsal."""
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from check_packages import ROOT, check


def csv_newlines(content):
    if b"\r\r\n" in content:
        raise ValueError("CSV에 중복 CR 줄바꿈이 있습니다")


def sequence(records):
    def code(record):
        return {k:v for k,v in record["files"].items() if k != "README.md"}
    finals=[]
    for group in {x["group"] for x in records}:
        items=[x for x in records if x["group"]==group]
        for item in items:
            if item["kind"]=="start" and item["day"]>1:
                previous=next(x for x in items if x["kind"]=="complete" and x["day"]==item["day"]-1)
                if code(previous)!=code(item):
                    raise ValueError("이전 완성본과 다음 출발본 코드가 다릅니다: "+item["id"])
        finals.append(max((x for x in items if x["kind"]=="complete"),key=lambda x:x["day"]))
    if any(code(x)!=code(finals[0]) for x in finals[1:]):
        raise ValueError("두 반 최종 코드가 다릅니다")


def stage(record):
    with zipfile.ZipFile(ROOT/record["archive"]) as archive:
        names=set(archive.namelist())
        for suffix in ["frontend/src/ClassificationResult.vue","backend/detect/provenance.py","backend/ontology/artifacts.py"]:
            if (("equipment-assistant/"+suffix) in names)!=("table" in record["features"]):
                raise ValueError("분류 단계 파일이 맞지 않습니다: "+record["id"]+" "+suffix)
        if "data" in record["features"] and "table" not in record["features"]:
            if "related_rows" in archive.read("equipment-assistant/backend/ontology/gateway.py").decode():
                raise ValueError("분류 전 출발본에 저장 분석 관계 조회가 들어갔습니다")
        count=0
        for name in names:
            if name.endswith(".csv"):
                csv_newlines(archive.read(name));count+=1
    return {"id":record["id"],"features":record["features"],"csv_files":count}


def main():
    manifest=json.loads((ROOT/"30_기록/공통코드_매니페스트.json").read_text(encoding="utf-8"))
    records=manifest["records"]
    csv_newlines(b"a,b\r\n1,2\r\n")
    try:csv_newlines(b"a,b\r\r\n")
    except ValueError:pass
    else:raise AssertionError("중복 CR fixture를 거부하지 못했습니다")
    sequence(records)
    damaged=json.loads(json.dumps(records))
    target=next(x for x in damaged if x["kind"]=="start" and x["day"]>1)
    target["files"]["fixture_unexpected.py"]="not-a-real-file"
    try:sequence(damaged)
    except ValueError:pass
    else:raise AssertionError("출발본 변경 fixture를 거부하지 못했습니다")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(check,records))
    stages=[stage(record) for record in records]
    report={"stamp":manifest["stamp"],"scope":"새 ZIP 재추출·집합/해시·구문·API import. 모델/DB 업무/완주 미실행","results":results}
    (ROOT/"30_기록/공통코드_구조검사.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    report={"stamp":manifest["stamp"],"checked":stages,"previous_complete_equals_next_start":True,
            "final_cohorts_identical":True,"csv_newlines_valid":True,"broken_csv_and_sequence_rejected":True,
            "scope":"분류 화면/행 관계 포함 시점, CSV 줄바꿈, 코드 연속성. 전체 기능 의미/실행 미검증"}
    (ROOT/"30_기록/공통코드_단계대조.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"packages":len(results),"csv_files":sum(x["csv_files"] for x in stages),"sequence":"pass","negative_fixtures":"pass"}))


if __name__=="__main__":main()

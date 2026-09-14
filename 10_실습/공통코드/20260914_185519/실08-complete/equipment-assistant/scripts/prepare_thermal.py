"""Convert explicit temperature rows to display images with one fixed range and preserved split labels."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import csv
import json

from backend.common.config import ROOT, configured_path, mapping


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--temperatures",required=True,help="헤더 유무를 확인한 온도 CSV")
    parser.add_argument("--labels",required=True,help="row_index,id,label,split,side 열을 가진 대응표; row_index는 0기준")
    parser.add_argument("--has-header",action="store_true")
    parser.add_argument("--min-temperature",type=float,required=True)
    parser.add_argument("--max-temperature",type=float,required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--provenance",required=True)
    args=parser.parse_args()
    import numpy as np
    from PIL import Image
    low,high=args.min_temperature,args.max_temperature
    if not np.isfinite([low,high]).all() or low>=high:
        raise ValueError("온도 표현 범위를 확인하세요")
    output=configured_path(args.output)
    if not output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("변환 출력은 이 프로젝트 안의 새 폴더로 지정하세요")
    if output.exists():
        raise ValueError("기존 이미지 폴더를 덮지 않습니다")
    with configured_path(args.labels).open(encoding="utf-8-sig",newline="") as stream:
        labels=list(csv.DictReader(stream))
    if not labels:
        raise ValueError("라벨 대응표가 비어 있습니다")
    indexed={int(row["row_index"]):row for row in labels}
    if len(indexed)!=len(labels) or len({row["id"] for row in labels})!=len(labels):
        raise ValueError("라벨 대응표의 행 번호 또는 ID가 중복됩니다")
    for row in labels:
        if row["label"] not in {"0","1"} or row["split"] not in {"train","validation","test"}:
            raise ValueError("라벨과 분할 값을 확인하세요")
        if row["split"]=="train" and row["label"]!="0":
            raise ValueError("정상 기반 모델의 학습에는 정상 이미지만 사용합니다")
        if Path(row["id"]).name!=row["id"] or not row["id"]:
            raise ValueError("샘플 ID에는 경로를 넣지 않습니다")
    shape=mapping()["vision"]["shape"]
    output.mkdir(parents=True)
    manifest=[]
    clipped=0
    with configured_path(args.temperatures).open(encoding="utf-8-sig",newline="") as stream:
        reader=csv.reader(stream)
        if args.has_header:
            next(reader)
        for index,row in enumerate(reader):
            if index not in indexed:
                raise ValueError(f"온도 행과 연결할 라벨이 없습니다: {index}")
            values=np.asarray(row,dtype=float)
            if values.size!=shape[0]*shape[1] or not np.isfinite(values).all():
                raise ValueError(f"온도 행의 크기 또는 수치 오류: {index}")
            clipped+=int(((values<low)|(values>high)).sum())
            pixels=np.clip((values-low)/(high-low),0,1).reshape(shape)
            image_path=output/(indexed[index]["id"]+".png")
            Image.fromarray((pixels*255).round().astype("uint8")).convert("RGB").save(image_path)
            label=indexed[index]
            manifest.append({"id":label["id"],"path":str(image_path.relative_to(ROOT)).replace('\\','/'),
                "label":label["label"],"split":label["split"],"side":label["side"],"provenance":args.provenance})
    if len(manifest)!=len(labels):
        raise ValueError("온도 행 수와 라벨 대응표 수가 다릅니다. 부분 출력을 완료 자료로 사용하지 마세요")
    with (output/"manifest.csv").open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(manifest[0]));writer.writeheader();writer.writerows(manifest)
    (output/"conversion.json").write_text(json.dumps({"shape":shape,"range":[low,high],"clipped_pixels":clipped,
        "samples":len(manifest),"provenance":args.provenance,"representation":"온도 범위 고정 회색조 RGB; 실제 RGB 사진 아님"},ensure_ascii=False,indent=2),encoding="utf-8")
    sys.stdout.write("이미지와 라벨·분할 대응표를 저장했습니다. 모델은 실행하지 않았습니다.\n")


if __name__=="__main__":
    main()

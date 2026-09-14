"""Download a named pretrained feature extractor only on explicit operator request."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import argparse
import os

from backend.common.config import configured_path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--method",choices=["padim","patchcore"],required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--download",action="store_true")
    args=parser.parse_args()
    if not args.download or os.getenv("ALLOW_MODEL_DOWNLOADS","false").lower()!="true":
        raise ValueError("가중치 다운로드를 명시적으로 선택해야 합니다")
    output=configured_path(args.output)
    if output.exists():
        raise ValueError("기존 가중치 파일을 덮지 않습니다")
    import torch
    from anomalib.models import Padim, Patchcore
    model=(Padim if args.method=="padim" else Patchcore)(backbone="resnet18",pre_trained=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    torch.save(model.model.feature_extractor.feature_extractor.state_dict(),output)
    sys.stdout.write(f"특징 추출기 가중치 저장: {output.name}\n")


if __name__=="__main__":
    main()

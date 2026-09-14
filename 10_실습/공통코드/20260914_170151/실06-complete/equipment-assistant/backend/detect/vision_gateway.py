"""Run PaDiM/PatchCore on an explicit normal-only training split using CPU."""
import csv
from pathlib import Path

from backend.common.config import ROOT, configured_path, mapping
from backend.common.log import span


def manifest():
    config=mapping()["vision"]
    with configured_path(config["manifest"]).open(encoding="utf-8-sig",newline="") as stream:
        rows=list(csv.DictReader(stream))
    required={"id","path","label","split","side","provenance"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("이미지 매니페스트의 항목을 확인하세요")
    ids=[row["id"] for row in rows]
    if len(set(ids))!=len(ids):
        raise ValueError("이미지 ID가 중복됩니다")
    paths=[]
    for row in rows:
        path=configured_path(row["path"]).resolve()
        if not path.is_file() or row["split"] not in {"train","validation","test"} or row["label"] not in {"0","1"}:
            raise ValueError("이미지 파일·라벨·분할을 확인하세요")
        if row["split"]=="train" and row["label"]!="0":
            raise ValueError("PaDiM/PatchCore 학습 구간은 정상 이미지만 사용합니다")
        paths.append(path)
    if len(set(paths))!=len(paths):
        raise ValueError("같은 이미지 파일이 여러 분할에 포함됐습니다")
    return rows


def run(side: str, method: str, backbone_path: str, output_name: str):
    # An explicit, already downloaded backbone avoids an implicit network download during fitting.
    if method not in {"padim","patchcore"}:
        raise ValueError("비전 방법은 padim 또는 patchcore입니다")
    weights=configured_path(backbone_path)
    if not weights.is_file():
        raise ValueError("사전에 받은 특징 추출기 가중치 파일이 필요합니다")
    if not output_name or Path(output_name).name!=output_name:
        raise ValueError("출력 이름은 파일명 한 개로 지정하세요")
    selected=[row for row in manifest() if row["side"]==side]
    for split in ("train","validation","test"):
        group=[row for row in selected if row["split"]==split]
        if not group or (split!="train" and {row["label"] for row in group}!={"0","1"}):
            raise ValueError("좌·우를 나누고 학습 정상 및 검증/평가의 정상·불량 표본을 남기세요")
    import torch
    from anomalib.data import ImageBatch
    from anomalib.engine import Engine
    from anomalib.models import Padim, Patchcore
    from anomalib.metrics import AUROC,F1Score,Evaluator
    from anomalib.pre_processing import PreProcessor
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset
    from torchvision.transforms import v2
    class Images(Dataset):
        def __init__(self,split):
            self.rows=[row for row in selected if row["split"]==split]
            self.transform=v2.Compose([v2.Resize((256,320)),v2.ToImage(),v2.ToDtype(torch.float32,scale=True)])
        def __len__(self):
            return len(self.rows)
        def __getitem__(self,index):
            row=self.rows[index]
            with Image.open(configured_path(row["path"])) as image:
                tensor=self.transform(image.convert("RGB"))
            return {"image":tensor,"gt_label":torch.tensor(int(row["label"])),"image_path":row["path"]}
    def collate(items):
        return ImageBatch(image=torch.stack([item["image"] for item in items]),
                          gt_label=torch.stack([item["gt_label"] for item in items]),
                          image_path=[item["image_path"] for item in items])
    loaders={split:DataLoader(Images(split),batch_size=4,shuffle=False,num_workers=0,collate_fn=collate)
             for split in ("train","validation","test")}
    evaluator=Evaluator(test_metrics=[AUROC(fields=['pred_score','gt_label'],prefix='image_'),
                                      F1Score(fields=['pred_label','gt_label'],prefix='image_')])
    preprocessor=PreProcessor(transform=v2.Compose([v2.Resize((256,320)),
        v2.Normalize(mean=[.485,.456,.406],std=[.229,.224,.225])]))
    model=(Padim if method=="padim" else Patchcore)(backbone="resnet18",pre_trained=False,
                                                 pre_processor=preprocessor,evaluator=evaluator,visualizer=False)
    # The feature extractor's parameters come from the named local file, never random features.
    checkpoint=torch.load(weights,map_location="cpu",weights_only=True)
    model.model.feature_extractor.feature_extractor.load_state_dict(checkpoint,strict=True)
    folder=ROOT/"artifacts"/output_name
    if folder.exists():
        raise ValueError("기존 비전 결과를 덮지 않습니다")
    with span("detect","detect.model","backend/detect/vision_gateway.py:run",method=method,side=side):
        engine=Engine(accelerator="cpu",devices=1,logger=False,enable_progress_bar=False,default_root_dir=folder)
        engine.fit(model=model,train_dataloaders=loaders["train"],val_dataloaders=loaders["validation"])
        result=engine.test(model=model,dataloaders=loaders["test"])
        predictions=[]
        import numpy as np
        by_path={row['path']:row for row in selected}
        for split in ('validation','test'):
            batches=engine.predict(model=model,dataloaders=loaders[split],return_predictions=True)
            if batches is None:raise ValueError('이미지 예측 결과가 반환되지 않았습니다')
            for batch in batches:
                for i,image_path in enumerate(batch.image_path):
                    row=by_path[image_path]
                    identity=row['id']
                    if Path(identity).name!=identity or not identity:raise ValueError('이미지 ID는 파일명으로 사용할 수 있는 한 항목이어야 합니다')
                    anomaly=batch.anomaly_map[i].detach().cpu().squeeze().numpy()
                    if anomaly.ndim!=2 or not np.isfinite(anomaly).all():raise ValueError('열지도 값이 유효하지 않습니다')
                    # Postprocessed score range is displayed consistently; no per-image min-max stretch.
                    display=np.clip(anomaly,0,1)
                    colors=np.stack([display,display*.55,1-display],axis=-1)
                    heatmap=folder/(identity+'-heatmap.png')
                    heatmap.parent.mkdir(parents=True,exist_ok=True)
                    Image.fromarray((colors*255).astype('uint8')).save(heatmap)
                    predictions.append({'id':identity,'split':split,'expected':int(row['label']),
                        'score':float(batch.pred_score[i].detach().cpu()),'predicted':int(batch.pred_label[i].detach().cpu()),
                        'image_path':image_path,'heatmap_path':str(heatmap.relative_to(ROOT)),
                        'map_display':'후처리 점수 0~1 고정 색 범위. 실제 결함 위치 정답과 대조한 지도가 아님'})
    return {"method":method,"side":side,"metrics":result,"output":str(folder.relative_to(ROOT)),
            'predictions':predictions,
            "split_counts":{split:len(loader.dataset) for split,loader in loaders.items()},
            "provenance":sorted({row["provenance"] for row in selected}),
            "limitations":"온도 표현·제품 측면·분할 범위 안의 판정. LOT 연결 또는 원인 증명 아님"}

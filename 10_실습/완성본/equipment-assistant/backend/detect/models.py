"""Explicit CPU analyses; train/evaluation boundaries are part of each returned artifact."""
import os

from backend.common.config import settings
from backend.common.service import finite_number

from .rules import classification_summary, first_threshold_crossing


def table_classifier(rows: list[dict], feature_ids: list[int], label_id: int, label_values: dict,
                     train_fraction: float, split: str = "ordered", seed: int = 42):
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    if not .5 <= train_fraction <= .9 or len(rows) < 20:
        raise ValueError("학습 비율은 0.5~0.9, 입력은 20행 이상이어야 합니다")
    if not feature_ids or label_id in feature_ids or len(set(feature_ids)) != len(feature_ids):
        raise ValueError("특징 선택을 확인하세요. 정답 열은 입력 특징이 될 수 없습니다")
    features, labels = [], []
    for row in rows:
        raw_value = row.get(f"c{label_id}")
        raw_label = str(int(raw_value)) if isinstance(raw_value, float) and raw_value.is_integer() else str(raw_value).strip()
        if raw_label not in label_values:
            raise ValueError("매핑에 없는 라벨입니다. 삭제하거나 임의로 바꾸지 않았습니다")
        if type(label_values[raw_label]) is not int or label_values[raw_label] not in (0, 1):
            raise ValueError("라벨 매핑 결과는 정수 0 또는 1이어야 합니다")
        labels.append(label_values[raw_label])
        features.append([np.nan if row.get(f"c{identity}") is None else
                         finite_number(row[f"c{identity}"], "특징") for identity in feature_ids])
    x, y = np.asarray(features), np.asarray(labels)
    indices = np.arange(len(rows))
    if split == "ordered":
        cut = int(len(rows) * train_fraction)
        train, test = indices[:cut], indices[cut:]
    elif split == "random":
        train, test = train_test_split(indices, train_size=train_fraction, random_state=seed, stratify=y)
    else:
        raise ValueError("분할 방식은 ordered 또는 random입니다")
    if len(set(y[train])) < 2:
        raise ValueError("학습 구간에 한 라벨만 있습니다")
    if np.isnan(x[train]).all(axis=0).any():
        raise ValueError("학습 구간 전체가 결측인 특징이 있습니다")
    model = make_pipeline(SimpleImputer(strategy="median"),
                          RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=seed, n_jobs=1))
    model.fit(x[train], y[train])
    predicted = model.predict(x[test]).astype(int).tolist()
    summary = classification_summary(y[test].astype(int).tolist(), predicted, feature_ids,
                                     model.steps[-1][1].feature_importances_.tolist())
    return {**summary, "train_rows": len(train), "test_rows": len(test), "split": split,
            "features": feature_ids, "predictions": [{"row_no": rows[int(i)]["row_no"], "predicted": int(p),
                "expected": int(y[i])} for i, p in zip(test, predicted)],
            "limitations": "전처리는 학습 구간에서만 적합. 파일 순서는 실제 시각과 같다는 보장이 없음"}


def pyod_scores(values: list[float], baseline_count: int):
    import numpy as np
    from pyod.models.copod import COPOD
    if not 10 <= baseline_count < len(values):
        raise ValueError("기준 구간을 10개 이상 정하고 뒤에 평가 구간을 남기세요")
    x = np.asarray([finite_number(value, "PyOD 입력") for value in values]).reshape(-1, 1)
    model = COPOD(contamination=settings()["detect"]["contamination"])
    model.fit(x[:baseline_count])
    scored = model.decision_function(x[baseline_count:])
    predicted = model.predict(x[baseline_count:])
    return {"method": "PyOD COPOD", "baseline_count": baseline_count,
            "scores": scored.tolist(), "predictions": predicted.astype(int).tolist(),
            "threshold": float(model.threshold_), "score_meaning": "이상 점수. 불량 확률 아님"}


def chronos_forecast(values: list[float], horizon: int | None = None):
    import torch
    from chronos import BaseChronosPipeline
    config = settings()["detect"]
    horizon = horizon or config["forecast_horizon"]
    minimum=int(config.get('forecast_min_input',200))
    if len(values) < minimum or not 1 <= horizon <= 64:
        raise ValueError(f"예측은 입력 {minimum}개 이상, 미래 1~64개를 사용합니다")
    pipeline = BaseChronosPipeline.from_pretrained(config["forecast_model"], device_map="cpu",
                torch_dtype=torch.float32, local_files_only=os.getenv("ALLOW_MODEL_DOWNLOADS", "false").lower() != "true")
    context = torch.tensor([finite_number(value, "예측 입력") for value in values], dtype=torch.float32)
    with torch.no_grad():
        quantiles, mean = pipeline.predict_quantiles(context, prediction_length=horizon, quantile_levels=[.1,.5,.9])
    return {"model": config["forecast_model"], "horizon": horizon,
            "lower": quantiles[0, :, 0].tolist(), "median": quantiles[0, :, 1].tolist(),
            "upper": quantiles[0, :, 2].tolist(), "mean": mean[0].tolist(),
            "axis": "다음 샷 순서", "interval": "모델의 0.1~0.9 분위수. 실제 포함률 실측 아님"}


def forecast_evaluation(values,horizon,evaluate_last=True):
    horizon=horizon or settings()['detect']['forecast_horizon']
    if not evaluate_last:
        return {**chronos_forecast(values,horizon),'evaluation':'미래 예측: 정답 관측 전','input_rows':len(values)}
    if type(horizon)is not int or not 1<=horizon<=64:raise ValueError('평가 길이는 1~64입니다')
    history=values[:-horizon];expected=[finite_number(x,'평가 정답') for x in values[-horizon:]]
    result=chronos_forecast(history,horizon)
    predicted=result['median'];baseline=[finite_number(history[-1],'직전값')]*horizon
    if len(predicted)!=len(expected):raise ValueError('예측과 평가 정답 길이가 다릅니다')
    mae=lambda series:sum(abs(a-b) for a,b in zip(series,expected))/horizon
    result.update(expected=expected,last_value_baseline=baseline,
        evaluation='마지막 관측 구간을 입력에서 제외한 홀드아웃 평가',input_rows=len(history),
        metrics={'median_mae':mae(predicted),'last_value_mae':mae(baseline),
                 'interval_coverage':sum(lo<=x<=hi for lo,x,hi in zip(result['lower'],expected,result['upper']))/horizon},
        axis='입력에서 남겨 둔 뒤쪽 샷 순서',interval='0.1~0.9 분위수와 이 홀드아웃에서의 포함률. 다른 구간의 보장 아님')
    return result


def threshold_forecast(values: list[float], threshold: float, direction: str):
    forecast = chronos_forecast(values)
    forecast.update(threshold=threshold, direction=direction,
        median_crossing=first_threshold_crossing(forecast["median"], threshold, direction),
        lower_crossing=first_threshold_crossing(forecast["lower"], threshold, direction),
        upper_crossing=first_threshold_crossing(forecast["upper"], threshold, direction),
        interpretation="예측 구간 내 임계 도달 순서. 실제 고장까지 남은 수명 또는 시간으로 바꾸지 않음")
    return forecast


def cmapss_regression(train_path, test_path, labels_path, sensor_indices: list[int]):
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    train = pd.read_csv(train_path, sep=r"\s+", header=None)
    test = pd.read_csv(test_path, sep=r"\s+", header=None)
    truth = pd.read_csv(labels_path, sep=r"\s+", header=None)[0].to_numpy()
    if train.shape[1] != 26 or test.shape[1] != 26 or not sensor_indices:
        raise ValueError("C-MAPSS의 26열과 센서 선택을 확인하세요")
    if any(not 5 <= index <= 25 for index in sensor_indices):
        raise ValueError("센서 위치는 0기준 5~25입니다. 장비 ID와 정답을 특징으로 쓰지 않습니다")
    train_rul = train.groupby(0)[1].transform("max") - train[1]
    last = test.sort_values([0,1]).groupby(0).tail(1).sort_values(0)
    if len(last) != len(truth):
        raise ValueError("평가 장비 수와 RUL 정답 수가 다릅니다")
    model = RandomForestRegressor(n_estimators=100, random_state=settings()["detect"]["seed"], n_jobs=1)
    model.fit(train[sensor_indices], train_rul)
    predicted = model.predict(last[sensor_indices])
    return {"mae_cycles":float(mean_absolute_error(truth,predicted)),
            "rmse_cycles":float(np.sqrt(mean_squared_error(truth,predicted))),
            "units":len(last), "predicted":predicted.tolist(), "expected":truth.tolist(),
            "provenance":"NASA C-MAPSS 대체 도메인", "claim":"제트 엔진 시뮬레이션의 사이클 기준 평가. 사출 RUL 검증 아님"}

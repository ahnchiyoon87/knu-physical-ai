"""Explicit CPU analyses; train/evaluation boundaries are part of each returned artifact."""
import os
from backend.common.config import settings
from backend.common.service import finite_number

def pyod_scores(values: list[float], baseline_count: int):
    import numpy as np
    from pyod.models.copod import COPOD
    if not 10 <= baseline_count < len(values):
        raise ValueError('기준 구간을 10개 이상 정하고 뒤에 평가 구간을 남기세요')
    x = np.asarray([finite_number(value, 'PyOD 입력') for value in values]).reshape(-1, 1)
    model = COPOD(contamination=settings()['detect']['contamination'])
    model.fit(x[:baseline_count])
    scored = model.decision_function(x[baseline_count:])
    predicted = model.predict(x[baseline_count:])
    return {'method': 'PyOD COPOD', 'baseline_count': baseline_count, 'scores': scored.tolist(), 'predictions': predicted.astype(int).tolist(), 'threshold': float(model.threshold_), 'score_meaning': '이상 점수. 불량 확률 아님'}

def chronos_forecast(values: list[float], horizon: int | None=None):
    import torch
    from chronos import BaseChronosPipeline
    config = settings()['detect']
    horizon = horizon or config['forecast_horizon']
    minimum = int(config.get('forecast_min_input', 200))
    if len(values) < minimum or not 1 <= horizon <= 64:
        raise ValueError(f'예측은 입력 {minimum}개 이상, 미래 1~64개를 사용합니다')
    pipeline = BaseChronosPipeline.from_pretrained(config['forecast_model'], device_map='cpu', torch_dtype=torch.float32, local_files_only=os.getenv('ALLOW_MODEL_DOWNLOADS', 'false').lower() != 'true')
    context = torch.tensor([finite_number(value, '예측 입력') for value in values], dtype=torch.float32)
    with torch.no_grad():
        quantiles, mean = pipeline.predict_quantiles(context, prediction_length=horizon, quantile_levels=[0.1, 0.5, 0.9])
    return {'model': config['forecast_model'], 'horizon': horizon, 'lower': quantiles[0, :, 0].tolist(), 'median': quantiles[0, :, 1].tolist(), 'upper': quantiles[0, :, 2].tolist(), 'mean': mean[0].tolist(), 'axis': '다음 샷 순서', 'interval': '모델의 0.1~0.9 분위수. 실제 포함률 실측 아님'}

def forecast_evaluation(values, horizon, evaluate_last=True):
    horizon = horizon or settings()['detect']['forecast_horizon']
    if not evaluate_last:
        return {**chronos_forecast(values, horizon), 'evaluation': '미래 예측: 정답 관측 전', 'input_rows': len(values)}
    if type(horizon) is not int or not 1 <= horizon <= 64:
        raise ValueError('평가 길이는 1~64입니다')
    history = values[:-horizon]
    expected = [finite_number(x, '평가 정답') for x in values[-horizon:]]
    result = chronos_forecast(history, horizon)
    predicted = result['median']
    baseline = [finite_number(history[-1], '직전값')] * horizon
    if len(predicted) != len(expected):
        raise ValueError('예측과 평가 정답 길이가 다릅니다')
    mae = lambda series: sum((abs(a - b) for a, b in zip(series, expected))) / horizon
    result.update(expected=expected, last_value_baseline=baseline, evaluation='마지막 관측 구간을 입력에서 제외한 홀드아웃 평가', input_rows=len(history), metrics={'median_mae': mae(predicted), 'last_value_mae': mae(baseline), 'interval_coverage': sum((lo <= x <= hi for lo, x, hi in zip(result['lower'], expected, result['upper']))) / horizon}, axis='입력에서 남겨 둔 뒤쪽 샷 순서', interval='0.1~0.9 분위수와 이 홀드아웃에서의 포함률. 다른 구간의 보장 아님')
    return result

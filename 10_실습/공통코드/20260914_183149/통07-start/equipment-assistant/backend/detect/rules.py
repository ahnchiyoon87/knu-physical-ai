"""Pure alarm calculations preserve ordering, provenance and suppression counts."""
from statistics import fmean, pstdev
from backend.common.service import finite_number

def detect_rows(rows: list[dict], definition: dict) -> list[dict]:
    mode = definition['mode']
    if mode not in {'absolute', 'relative', 'combined', 'multichannel'}:
        raise ValueError('지원하지 않는 규칙입니다')
    if mode == 'multichannel':
        return detect_multichannel(rows, definition)
    minimum = int(definition.get('baseline_count', 10))
    suppression = int(definition.get('suppression_shots', 0))
    if minimum < 2 or suppression < 0:
        raise ValueError('기준 구간과 억제 간격을 확인하세요')
    groups = {}
    for row in rows:
        groups.setdefault(row['lot_id'], []).append(row)
    alarms = []
    for samples in groups.values():
        samples = sorted(samples, key=lambda row: row['row_no'])
        if len({x['row_no'] for x in samples}) != len(samples):
            raise ValueError('같은 LOT 안에 순서가 중복됩니다')
        valid = [finite_number(x['value'], '감지값') for x in samples[:minimum] if x['value'] is not None]
        if mode != 'absolute' and len(valid) != minimum:
            raise ValueError('LOT 기준 구간에 필요한 유효 값이 부족합니다')
        mean = fmean(valid) if valid else None
        std = pstdev(valid) if valid else None
        last_notified = None
        for offset, row in enumerate(samples):
            if row['value'] is None:
                continue
            value = finite_number(row['value'], '감지값')
            low, high = (row.get('lower', definition.get('lower')), row.get('upper', definition.get('upper')))
            if mode in {'absolute', 'combined'} and low is None and (high is None):
                raise ValueError('적용할 절대 기준이 없습니다')
            absolute = low is not None and value < low or (high is not None and value > high)
            if mode != 'absolute' and offset < minimum:
                continue
            if mode != 'absolute' and definition.get('relative_unit') == 'percent':
                if mean == 0:
                    raise ValueError('기준 평균 0에서는 평균 대비 비율을 계산할 수 없습니다')
                relative = abs(value - mean) / abs(mean) * 100 > definition['width']
            elif mode != 'absolute' and std == 0:
                relative = value != mean
            else:
                relative = False if mode == 'absolute' else abs(value - mean) > definition['width'] * std
            flagged = absolute if mode == 'absolute' else relative if mode == 'relative' else absolute and relative
            if flagged:
                suppressed = last_notified is not None and offset - last_notified <= suppression
                if not suppressed:
                    last_notified = offset
                alarms.append({**row, 'baseline_mean': mean, 'baseline_std': std, 'suppressed': suppressed, 'priority': definition.get('priority', 'review'), 'rule_version': definition['version']})
    return alarms

def detect_multichannel(rows, definition):
    """Apply AND/OR to named channels using only their preceding baseline rows."""
    conditions = definition.get('conditions', [])
    if len(conditions) < 2 or definition.get('operator') not in {'and', 'or'}:
        raise ValueError('조합 규칙은 두 채널 이상과 and/or가 필요합니다')
    minimum = int(definition.get('baseline_count', 200))
    suppression = int(definition.get('suppression_shots', 0))
    if minimum < 2 or suppression < 0:
        raise ValueError('기준 구간과 억제 간격을 확인하세요')
    groups = {}
    alarms = []
    for row in rows:
        groups.setdefault(row['lot_id'], []).append(row)
    for samples in groups.values():
        samples = sorted(samples, key=lambda row: row['row_no'])
        if len({row['row_no'] for row in samples}) != len(samples):
            raise ValueError('순서 중복')
        if len(samples) <= minimum:
            raise ValueError('조합 감지의 기준 뒤 관측이 부족합니다')
        baselines = {}
        for condition in conditions:
            cid = str(condition['column_id'])
            if condition['direction'] not in {'above', 'below'}:
                raise ValueError('조합 방향을 확인하세요')
            if finite_number(condition['percent'], '변화율') <= 0:
                raise ValueError('변화율은 양수여야 합니다')
            values = [row['channels'].get(cid) for row in samples[:minimum]]
            if any((value is None for value in values)):
                raise ValueError('조합 기준 구간에 결측이 있습니다')
            baselines[cid] = fmean((finite_number(value, '채널값') for value in values))
            if baselines[cid] == 0:
                raise ValueError('기준 평균 0에서는 변화율을 계산할 수 없습니다')
        last = None
        for offset, row in enumerate(samples[minimum:], minimum):
            checks = []
            details = []
            if any((row['channels'].get(str(c['column_id'])) is None for c in conditions)):
                raise ValueError('조합 감지 대상에 결측이 있습니다')
            for condition in conditions:
                cid = str(condition['column_id'])
                value = finite_number(row['channels'][cid], '채널값')
                change = (value - baselines[cid]) / abs(baselines[cid]) * 100
                hit = change > condition['percent'] if condition['direction'] == 'above' else change < -condition['percent']
                checks.append(hit)
                details.append({'column_id': int(cid), 'value': value, 'baseline': baselines[cid], 'percent_change': change, 'matched': hit})
            if all(checks) if definition['operator'] == 'and' else any(checks):
                suppressed = last is not None and offset - last <= suppression
                if not suppressed:
                    last = offset
                alarms.append({**row, 'conditions': details, 'suppressed': suppressed, 'priority': definition.get('priority', 'review'), 'rule_version': definition['version']})
    return alarms

def classification_counts(expected: list[int], predicted: list[int]) -> dict:
    if not expected or len(expected) != len(predicted):
        raise ValueError('비교할 라벨 개수가 일치하지 않거나 비어 있습니다')
    if any((type(x) is not int or x not in (0, 1) for x in expected + predicted)):
        raise ValueError('라벨은 0 또는 1이어야 합니다')
    tp = sum((a == b == 1 for a, b in zip(expected, predicted)))
    tn = sum((a == b == 0 for a, b in zip(expected, predicted)))
    fp = sum((a == 0 and b == 1 for a, b in zip(expected, predicted)))
    fn = sum((a == 1 and b == 0 for a, b in zip(expected, predicted)))
    return {'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn, 'n': len(expected), 'accuracy': (tp + tn) / len(expected), 'precision': tp / (tp + fp) if tp + fp else None, 'recall': tp / (tp + fn) if tp + fn else None}

def first_threshold_crossing(values: list[float], threshold: float, direction: str):
    if direction not in {'above', 'below'}:
        raise ValueError('임계 방향은 above 또는 below입니다')
    threshold = finite_number(threshold, '임계값')
    for index, value in enumerate(values, 1):
        value = finite_number(value, '예측값')
        if direction == 'above' and value >= threshold or (direction == 'below' and value <= threshold):
            return index
    return None

def classification_summary(expected, predicted, feature_ids, importances):
    """Compare the exact held-out rows and preserve fitted feature ordering."""
    metrics = classification_counts(expected, predicted)
    if not feature_ids or len(feature_ids) != len(importances) or len(set(feature_ids)) != len(feature_ids):
        raise ValueError('특징 ID와 중요도 개수가 일치하지 않거나 중복됩니다')
    weights = [finite_number(value, '특징 중요도') for value in importances]
    if any((value < 0 for value in weights)):
        raise ValueError('특징 중요도는 음수일 수 없습니다')
    return {'metrics': metrics, 'baseline': {'method': 'always_zero', 'evaluation': '모델과 동일한 평가 행', 'metrics': classification_counts(expected, [0] * len(expected))}, 'feature_importances': [{'column_id': identity, 'importance': value} for identity, value in zip(feature_ids, weights)], 'importance_meaning': '학습된 숲의 불순도 감소 기반 중요도. 값 종류가 많은 열에 편향될 수 있으며 인과나 불량 확률이 아님'}

"""Pure alarm calculations preserve ordering, provenance and suppression counts."""
from backend.common.service import finite_number

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

def classification_summary(expected, predicted, feature_ids, importances):
    """Compare the exact held-out rows and preserve fitted feature ordering."""
    metrics = classification_counts(expected, predicted)
    if not feature_ids or len(feature_ids) != len(importances) or len(set(feature_ids)) != len(feature_ids):
        raise ValueError('특징 ID와 중요도 개수가 일치하지 않거나 중복됩니다')
    weights = [finite_number(value, '특징 중요도') for value in importances]
    if any((value < 0 for value in weights)):
        raise ValueError('특징 중요도는 음수일 수 없습니다')
    return {'metrics': metrics, 'baseline': {'method': 'always_zero', 'evaluation': '모델과 동일한 평가 행', 'metrics': classification_counts(expected, [0] * len(expected))}, 'feature_importances': [{'column_id': identity, 'importance': value} for identity, value in zip(feature_ids, weights)], 'importance_meaning': '학습된 숲의 불순도 감소 기반 중요도. 값 종류가 많은 열에 편향될 수 있으며 인과나 불량 확률이 아님'}

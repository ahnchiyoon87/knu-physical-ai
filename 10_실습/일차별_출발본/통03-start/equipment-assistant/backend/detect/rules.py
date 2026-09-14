"""Pure alarm calculations preserve ordering, provenance and suppression counts."""

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

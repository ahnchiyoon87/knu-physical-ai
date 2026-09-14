"""Explicit CPU analyses; train/evaluation boundaries are part of each returned artifact."""
from backend.common.service import finite_number
from .rules import classification_summary

def table_classifier(rows: list[dict], feature_ids: list[int], label_id: int, label_values: dict, train_fraction: float, split: str='ordered', seed: int=42):
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    if not 0.5 <= train_fraction <= 0.9 or len(rows) < 20:
        raise ValueError('학습 비율은 0.5~0.9, 입력은 20행 이상이어야 합니다')
    if not feature_ids or label_id in feature_ids or len(set(feature_ids)) != len(feature_ids):
        raise ValueError('특징 선택을 확인하세요. 정답 열은 입력 특징이 될 수 없습니다')
    features, labels = ([], [])
    for row in rows:
        raw_value = row.get(f'c{label_id}')
        raw_label = str(int(raw_value)) if isinstance(raw_value, float) and raw_value.is_integer() else str(raw_value).strip()
        if raw_label not in label_values:
            raise ValueError('매핑에 없는 라벨입니다. 삭제하거나 임의로 바꾸지 않았습니다')
        if type(label_values[raw_label]) is not int or label_values[raw_label] not in (0, 1):
            raise ValueError('라벨 매핑 결과는 정수 0 또는 1이어야 합니다')
        labels.append(label_values[raw_label])
        features.append([np.nan if row.get(f'c{identity}') is None else finite_number(row[f'c{identity}'], '특징') for identity in feature_ids])
    x, y = (np.asarray(features), np.asarray(labels))
    indices = np.arange(len(rows))
    if split == 'ordered':
        cut = int(len(rows) * train_fraction)
        train, test = (indices[:cut], indices[cut:])
    elif split == 'random':
        train, test = train_test_split(indices, train_size=train_fraction, random_state=seed, stratify=y)
    else:
        raise ValueError('분할 방식은 ordered 또는 random입니다')
    if len(set(y[train])) < 2:
        raise ValueError('학습 구간에 한 라벨만 있습니다')
    if np.isnan(x[train]).all(axis=0).any():
        raise ValueError('학습 구간 전체가 결측인 특징이 있습니다')
    model = make_pipeline(SimpleImputer(strategy='median'), RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=seed, n_jobs=1))
    model.fit(x[train], y[train])
    predicted = model.predict(x[test]).astype(int).tolist()
    summary = classification_summary(y[test].astype(int).tolist(), predicted, feature_ids, model.steps[-1][1].feature_importances_.tolist())
    return {**summary, 'train_rows': len(train), 'test_rows': len(test), 'split': split, 'features': feature_ids, 'predictions': [{'row_no': rows[int(i)]['row_no'], 'predicted': int(p), 'expected': int(y[i])} for i, p in zip(test, predicted)], 'limitations': '전처리는 학습 구간에서만 적합. 파일 순서는 실제 시각과 같다는 보장이 없음'}

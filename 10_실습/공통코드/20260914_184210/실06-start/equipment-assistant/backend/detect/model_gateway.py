"""Model jobs read configured sources and persist provenance-aware artifacts."""
from uuid import uuid4
from psycopg import sql
from psycopg.types.json import Jsonb
from backend.common.config import configured_path, mapping, source, analysis_source
from backend.common.gateway import database
from backend.common.log import span
from . import models
from .provenance import bind_predictions
from .gateway import all_series

def table_rows(profile: str, source_id: str):
    config = analysis_source(source_id, profile)
    with database(readonly=True) as db:
        return db.execute(sql.SQL('SELECT * FROM lab.{} ORDER BY row_no').format(sql.Identifier(config['table']))).fetchall()

def job(profile: str, source_id: str, method: str, parameters: dict):
    config = analysis_source(source_id, profile) if method not in {'rul', 'vision'} else None
    provenance = config['provenance'] if config else ''
    target = f'{profile}:{source_id}'
    identity = str(uuid4())
    edges = []
    with span('detect', 'detect.model', 'backend/detect/model_gateway.py:job', method=method) as observed:
        if method == 'table':
            numeric = {c['id'] for c in config['columns'] if c['type'] == 'number'}
            if not set(parameters['feature_ids']).issubset(numeric):
                raise ValueError('선택한 특징이 수치 열 사전에 없습니다')
            rows = table_rows(profile, source_id)
            result = models.table_classifier(rows, parameters['feature_ids'], config['label_column_id'], config['label_values'], parameters.get('train_fraction', 0.7), parameters.get('split', 'ordered'))
            with database() as db:
                imported = db.execute('SELECT id,file_hash,mapping_hash FROM lab.imports WHERE profile=%s AND source_id=%s', (profile, source_id)).fetchone()
            result, edges = bind_predictions(result, rows, profile, source_id, imported, identity)
        elif method in {'forecast', 'pyod', 'threshold'}:
            if not parameters.get('lot_id'):
                raise ValueError('비교할 LOT 하나를 명시하세요')
            rows = all_series(profile, source_id, parameters['column_id'], parameters['lot_id'])
            if any((row['value'] is None for row in rows)):
                raise ValueError('결측이 있습니다. 처리 기준을 먼저 정하세요')
            values = [row['value'] for row in rows]
            if method == 'pyod':
                result = models.pyod_scores(values, parameters['baseline_count'])
            elif method == 'forecast':
                result = models.forecast_evaluation(values, parameters.get('horizon'), parameters.get('evaluate_last', True))
            else:
                result = models.threshold_forecast(values, parameters['threshold'], parameters['direction'])
            result['lot_id'] = parameters['lot_id']
            result['column_id'] = parameters['column_id']
        elif method == 'rul':
            folder = configured_path(mapping()['rul']['path'])
            subset = parameters['subset']
            if subset not in {'FD001', 'FD002', 'FD003', 'FD004'}:
                raise ValueError('C-MAPSS 부분집합 번호를 확인하세요')
            result = models.cmapss_regression(folder / f'train_{subset}.txt', folder / f'test_{subset}.txt', folder / f'RUL_{subset}.txt', parameters['sensor_indices'])
            provenance = 'NASA C-MAPSS ' + subset + ': 모의 항공엔진 열화 자료'
            target = 'cmapss:' + subset
        elif method == 'vision':
            from .vision_gateway import run
            result = run(**parameters)
            provenance = '; '.join(result['provenance'])
            target = 'thermal:' + parameters['side']
        else:
            raise ValueError('지원하지 않는 분석 방법입니다')
        result.update(id=identity, method=method, profile=profile if config else 'external_dataset', source_id=source_id if config else target, source_provenance=provenance, parameters=parameters)
        with database() as db:
            db.execute("INSERT INTO lab.artifacts(id,kind,payload) VALUES(%s,'model',%s)", (identity, Jsonb(result)))
            graph = {'id': identity, 'kind': 'model_result', 'status': 'observed', 'provenance': provenance, 'targets': [target], 'edges': edges}
            db.execute('INSERT INTO lab.graph_outbox(id,payload) VALUES(%s,%s)', (identity, Jsonb(graph)))
        observed.update(artifact_id=identity)
    return result

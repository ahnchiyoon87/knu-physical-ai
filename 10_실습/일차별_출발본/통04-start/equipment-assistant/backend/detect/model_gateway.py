"""Model jobs read configured sources and persist provenance-aware artifacts."""
from uuid import uuid4
from psycopg import sql
from psycopg.types.json import Jsonb
from backend.common.config import configured_path, mapping, source, analysis_source
from backend.common.gateway import database
from backend.common.log import span
from . import models
from .gateway import all_series

def table_rows(profile: str, source_id: str):
    config = analysis_source(source_id, profile)
    with database(readonly=True) as db:
        return db.execute(sql.SQL('SELECT * FROM lab.{} ORDER BY row_no').format(sql.Identifier(config['table']))).fetchall()

def job(profile: str, source_id: str, method: str, parameters: dict):
    config = analysis_source(source_id, profile) if method not in {'rul', 'vision'} else None
    provenance = config['provenance'] if config else ''
    target = f'{profile}:{source_id}'
    with span('detect', 'detect.model', 'backend/detect/model_gateway.py:job', method=method) as observed:
        if method == 'table':
            numeric = {c['id'] for c in config['columns'] if c['type'] == 'number'}
            if not set(parameters['feature_ids']).issubset(numeric):
                raise ValueError('선택한 특징이 수치 열 사전에 없습니다')
            result = models.table_classifier(table_rows(profile, source_id), parameters['feature_ids'], config['label_column_id'], config['label_values'], parameters.get('train_fraction', 0.7), parameters.get('split', 'ordered'))
        else:
            if method == 'vision':
                from .vision_gateway import run
                result = run(**parameters)
                provenance = '; '.join(result['provenance'])
                target = 'thermal:' + parameters['side']
            else:
                raise ValueError('지원하지 않는 분석 방법입니다')
        identity = str(uuid4())
        result.update(id=identity, method=method, profile=profile if config else 'external_dataset', source_id=source_id if config else target, source_provenance=provenance, parameters=parameters)
        with database() as db:
            db.execute("INSERT INTO lab.artifacts(id,kind,payload) VALUES(%s,'model',%s)", (identity, Jsonb(result)))
            graph = {'id': identity, 'kind': 'model_result', 'status': 'observed', 'provenance': provenance, 'targets': [target]}
            db.execute('INSERT INTO lab.graph_outbox(id,payload) VALUES(%s,%s)', (identity, Jsonb(graph)))
        observed.update(artifact_id=identity)
    return result

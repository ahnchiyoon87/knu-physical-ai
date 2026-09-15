"""3일차 완성본의 실제 조회 결과를 저장한다. 컨테이너 내부 실행용."""
import importlib.util
import json
from pathlib import Path
from hydops.b4_ontology import graph

ROOT = Path('/course')


def load(track, filename):
    spec = importlib.util.spec_from_file_location(track, ROOT/'실습자료/3일차/완성본'/track/filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    output = ROOT/'작업기록/셋째날제작_20260915/관찰결과.json'
    if output.exists():
        raise FileExistsError(output)
    integrated = load('integrated', 'graph_lab.py')
    practical = load('practical', 'context_queries.py')
    record = {'scope': '실제 DB 조회 결과. UI 캡처가 아님.', 'graph_stats': graph.graph_stats()}
    record['labels'] = graph.run('MATCH (s:Sensor {sensor_id:$id}) RETURN labels(s) AS labels, s {.*} AS properties', id='HYD-01.TS1')
    record['basis'] = graph.run('MATCH (d:Driver)-[r:AFFECTS]->(s:Sensor) RETURN d.driver_id AS driver, s.sensor_id AS sensor, r.basis AS basis, r.source AS source, r.verified_causal AS verified ORDER BY driver, sensor')
    record['sops'] = {a: practical.applicable_sops(a, 'COOLING_ANOMALY') for a in ('HYD-01', 'HYD-02', 'HYD-03')}
    record['contexts'] = {a: practical.asset_context(a) for a in ('HYD-01', 'HYD-02', 'HYD-03', 'HYD-99')}
    record['sensor_fault_sop'] = practical.applicable_sops('HYD-01', 'SENSOR_FAULT')
    record['without_status_filter'] = integrated.run_read(integrated.Q_APPLICABLE_SOP.replace("sop.status = 'active' AND ", ''), asset_id='HYD-01', event_type='COOLING_ANOMALY')
    record['merge_same_ids'] = integrated.seed_check()
    record['merge_wrong_id'] = integrated.merge_if_same_as_seed(integrated.MERGE_SENSOR.replace("+ '.' +", "+ '-' +"), asset_id='HYD-01', **graph.SENSORS[0])
    record['wrong_id_after_rollback'] = graph.run('MATCH (s:Sensor {sensor_id:$id}) RETURN count(s) AS n', id='HYD-01-TS1')
    event_id = integrated.any_event_with_citation()
    assert event_id, '인용 사건 준비 필요'
    record['event_evidence'] = integrated.run_read(integrated.Q_EVENT_EVIDENCE, event_id=event_id)
    run_id = integrated.load_lab_cycle()
    try:
        record['cycle100_integrated'] = integrated.sensors_with_recent_values('HYD-01', run_id)
        record['cycle100_practical'] = practical.join_recent('HYD-01', run_id)
    finally:
        integrated.cleanup(run_id)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'cycle100': record['cycle100_integrated'], 'wrong_id': record['merge_wrong_id'], 'after_rollback': record['wrong_id_after_rollback']}, ensure_ascii=False))


if __name__ == '__main__':
    main()

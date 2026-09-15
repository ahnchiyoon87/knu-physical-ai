"""3일차 강사용 사전 준비: 실제 합성 관측에서 탐지하고 SOP 인용을 기록한다.

컨테이너 내부에서 실행한다. 유료 모델을 호출하거나 사람 승인·설비 조치를
대신 수행하지 않는다. 새 사건은 승인 대기에 남고 결과 파일에 ID를 기록한다.
"""
import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from hydops.b3_tsdb import store
from hydops.b4_ontology import graph
from hydops.b8_action import service
from hydops.config import SETTINGS
from hydops.runtime import PlantRuntime


def prepare(output: Path):
    if output.exists():
        raise FileExistsError(f'기존 기록 보존: {output}')
    if SETTINGS.agent_mode != 'offline':
        raise RuntimeError('HYDOPS_AGENT_MODE=offline 환경에서만 준비합니다.')
    if store.open_event('HYD-01', 'COOLING_ANOMALY'):
        raise RuntimeError('HYD-01 냉각 이상 사건이 이미 열려 있습니다. 기존 사건을 먼저 확인하세요.')
    runtime = PlantRuntime(
        assets=('HYD-01',), seed=42, scenario='lab-s03-citation-prerequisite',
        run_id=f'LAB-S03-EVIDENCE-{uuid.uuid4().hex[:8]}',
        start=datetime(2027, 1, 26, 9, 0, tzinfo=timezone.utc),
    )
    assert runtime.tick(30) == [], '초기 구간에서 예상 밖 사건 발생'
    runtime.sims['HYD-01'].inject_cooling_degradation(0.4)
    event = None
    for _ in range(180):
        events = runtime.tick()
        matches = [e for e in events if e['event_type'] == 'COOLING_ANOMALY']
        if matches:
            event = matches[0]
            break
    if event is None:
        raise RuntimeError(f'탐지 실패. 관측은 보존합니다: {runtime.run_id}')
    result = service.gather_evidence(event['event_id'], agent_mode='offline')
    evidence = graph.event_evidence(event['event_id'])
    current = store.get_event(event['event_id'])
    assert current['status'] == 'PENDING_APPROVAL', current['status']
    assert result['proposal']['citations'] and not result['citation_problems']
    assert evidence and evidence['citations']
    assert store.actions_for(event['event_id']) == []
    record = {
        'at': datetime.now(timezone.utc).isoformat(),
        'scope': '합성 데이터 런타임의 실제 탐지·offline 도구 검색·인용 연결. UI 조작/LLM/학생 완주 검증 아님.',
        'run_id': runtime.run_id, 'event_id': event['event_id'],
        'state': current['status'], 'detected_event': event,
        'agent_result': result, 'graph_evidence': evidence,
        'event_history': store.event_history(event['event_id']),
        'recent_observations': store.recent_window('HYD-01', 60, run_id=runtime.run_id),
        'simulator': runtime.sims['HYD-01'].snapshot(),
        'actions': [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({k: record[k] for k in ('run_id', 'event_id', 'state', 'graph_evidence')}, ensure_ascii=False, default=str))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    prepare(parser.parse_args().output)

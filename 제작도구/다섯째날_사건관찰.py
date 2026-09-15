"""지정한 사건의 실제 도구 조회·제안 검사·offline 제안을 기록한다.

컨테이너 내부 hydops 실행 환경에서 사용한다. 승인·조치·사건 상태 변경은 하지 않는다.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from hydops.b3_tsdb import store
from hydops.b7_agent.tools import build_tools
from hydops.b7_agent.agent import propose_for_event
from hydops.config import SETTINGS


def snapshot(event_id):
    return {'event': store.get_event(event_id),
            'history': store.event_history(event_id),
            'actions': store.actions_for(event_id)}


def observe(event_id, output):
    if output.exists():
        raise FileExistsError(output)
    if SETTINGS.agent_mode != 'offline':
        raise RuntimeError('offline 모드에서 실행하세요.')
    before = snapshot(event_id)
    ev = before['event']
    if ev is None:
        raise ValueError(f'존재하지 않는 사건: {event_id}')
    trace = []
    tool_list = build_tools(event_until=ev['window_end'], run_id=ev['run_id'], trace=trace)
    tools = {t.name: t for t in tool_list}
    call = lambda name, args: json.loads(tools[name].invoke(args))
    window = call('get_recent_window', {'asset_id': ev['asset_id'], 'seconds': 60})
    context = call('get_asset_context', {'asset_id': ev['asset_id']})
    sop = call('search_sop', {'asset_id': ev['asset_id'], 'event_type': ev['event_type'], 'query': '허용 조치'})
    actions = [a for a in context.get('allowed_actions', [])
               if a.get('requires_approval') and a.get('default_value') is not None
               and a.get('min_value') is not None]
    checks = []
    if actions:
        act = actions[0]
        citations = [{k: h[k] for k in ('doc_id', 'version', 'section')} for h in sop['hits'][:3]]
        for label, value in [('default', act['default_value']), ('below_minimum', act['min_value'] - 0.1)]:
            result = call('propose_action', {'event_id': event_id, 'action_id': act['action_id'],
                                           'value': value, 'citations': citations})
            checks.append({'case': label, 'result': result})
        if not any(c['check'] == 'value_in_range' and not c['ok'] for c in checks[1]['result']['checks']):
            raise AssertionError('범위 밖 값이 value_in_range 검사에서 거부되지 않았습니다.')
    proposal = propose_for_event(event_id, mode='offline')
    after = snapshot(event_id)
    unchanged = json.dumps(before, sort_keys=True, default=str) == json.dumps(after, sort_keys=True, default=str)
    record = {'at': datetime.now(timezone.utc).isoformat(),
              'scope': '지정 실제 사건의 읽기·제안 검사. 승인/실행/유료모델/UI/학생 완주 아님.',
              'event_id': event_id, 'before': before, 'after': after, 'unchanged': unchanged,
              'tool_schemas': {t.name: t.args for t in tool_list},
              'window': window, 'context': context, 'search': sop,
              'checks': checks, 'tool_trace': trace, 'proposal': proposal}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    if not unchanged:
        raise RuntimeError('관찰 중 사건/이력/조치가 달라졌습니다. 동시 작업 여부를 확인하세요. 기록은 보존했습니다.')
    print(json.dumps({'event_id': event_id, 'status': ev['status'], 'unchanged': unchanged,
                      'decision': proposal['proposal']['decision'],
                      'tools': [t['tool'] for t in proposal['tool_trace']],
                      'checks': checks}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('event_id')
    p.add_argument('output', type=Path)
    args = p.parse_args()
    observe(args.event_id, args.output)

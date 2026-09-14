"""Incremental workflow nodes, explicit approval interrupt and bounded replay."""
from typing import TypedDict
from uuid import uuid4
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from backend.common.config import env, settings
from backend.common.log import request_id
from backend.common.response import reply
from backend.data import service as data
from backend.detect import gateway as detect_gateway
from backend.detect import service as detect
from backend.ontology import service as ontology
from backend.process import gateway as process_gateway
from backend.rag import service as rag
from . import gateway
from . import drafts

class AgentState(TypedDict, total=False):
    rid: str
    profile: str
    source_id: str
    lot_id: str | None
    rule_id: str
    question: str
    provider: str
    events: dict
    documents: dict
    proposal: dict
    decision: dict
    response: dict
    steps: int
    visited: list[str]
    paths: dict
    graph_end: str
    autonomy: int
    draft_set: dict
    model_meta: dict

def step(state: AgentState, name: str) -> dict:
    request_id.set(state['rid'])
    visited = state.get('visited', [])
    count = state.get('steps', 0) + 1
    if name in visited or count > settings()['agent']['max_steps']:
        raise ValueError('진전 없는 반복 또는 에이전트 걸음 상한입니다')
    return {'steps': count, 'visited': visited + [name]}

async def observe(state: AgentState):
    changed = step(state, 'observe')
    result = await gateway.tool('query_events', {'profile': state['profile'], 'source_id': state['source_id'], 'lot_id': state.get('lot_id'), 'rid': state['rid']})
    changed['events'] = result
    if result['status'] != 'ok':
        changed['response'] = reply(state['rid'], status='insufficient' if result['status'] == 'none' else result['status'], reason=result['reason']).model_dump(mode='json')
    return changed

async def retrieve(state: AgentState):
    changed = step(state, 'retrieve')
    result = await gateway.tool('search_docs', {'profile': state['profile'], 'question': state['question'], 'rid': state['rid']})
    changed['documents'] = result
    if result['status'] != 'ok':
        changed['response'] = reply(state['rid'], status='insufficient' if result['status'] == 'none' else result['status'], reason=result['reason']).model_dump(mode='json')
    elif state.get('autonomy', 2) == 0:
        changed['response'] = reply(state['rid'], {'events': state['events']['answer'], 'paths': state.get('paths'), 'scope': '자율성 0: 근거 조회까지만 수행'}, evidence=result['evidence']).model_dump(mode='json')
    return changed

async def relate(state: AgentState):
    changed = step(state, 'relate')
    if not state.get('lot_id') or not state.get('graph_end'):
        changed['response'] = reply(state['rid'], status='insufficient', reason='LOT와 관계 탐색의 끝 대상 ID가 필요합니다').model_dump(mode='json')
        return changed
    result = await gateway.tool('graph_path', {'start': f"{state['profile']}:{state['source_id']}:lot:{state['lot_id']}", 'end': state['graph_end'], 'rid': state['rid']})
    changed['paths'] = result
    if result['status'] != 'ok':
        changed['response'] = reply(state['rid'], status='insufficient' if result['status'] == 'none' else result['status'], reason=result['reason']).model_dump(mode='json')
    return changed

async def propose(state: AgentState):
    changed = step(state, 'propose')
    rule = detect_gateway.rule(state['rule_id'])
    if rule is None:
        changed['response'] = reply(state['rid'], status='insufficient', reason='현재 규칙이 없습니다').model_dump()
        return changed
    candidate, meta = gateway.suggest(state['provider'], state['question'], state['events']['answer'], state['documents']['evidence'], rule, state.get('paths'))
    changed['model_meta'] = meta
    changed['draft_set'] = drafts.save(state, candidate)
    if state.get('autonomy', 2) == 1:
        changed['response'] = reply(state['rid'], changed['draft_set'], evidence=state['documents']['evidence'], meta=meta).model_dump(mode='json')
        return changed
    if candidate.get('propose') is not True:
        changed['response'] = reply(state['rid'], changed['draft_set'], status='insufficient', reason=candidate.get('rationale') or '변경 제안에 필요한 근거가 부족합니다', meta=meta).model_dump()
        return changed
    rows = state['events']['answer']['rows']
    indices = candidate.get('event_indices', [])
    if not indices or any((type(i) is not int or not 0 <= i < len(rows) for i in indices)):
        raise ValueError('모델이 선택한 이벤트 번호가 유효하지 않습니다')
    result = await gateway.tool('propose_action', {'rid': state['rid'], 'rule_id': state['rule_id'], 'event_ids': [rows[i]['id'] for i in indices], 'new_width': candidate['new_width'], 'rationale': candidate['rationale']})
    changed['proposal'] = result
    if result['status'] != 'pending_approval':
        changed['response'] = result
    return changed

async def await_approval(state: AgentState):
    proposal = state['proposal']['answer']
    signal = interrupt({'proposal_id': proposal['id'], 'version': proposal['version'], 'payload_hash': proposal['payload_hash']})
    if not isinstance(signal, dict) or signal.get('proposal_id') != proposal['id']:
        raise ValueError('재개 대상이 승인 대기 대상과 다릅니다')
    stored = process_gateway.proposal(proposal['id'])
    if stored is None or stored['status'] not in {'approved', 'rejected', 'recorded'}:
        raise ValueError('서버에 저장된 사람의 결정이 없습니다')
    changed = step(state, 'approval')
    if stored['status'] == 'rejected':
        changed['response'] = reply(state['rid'], {'proposal_id': stored['id'], 'decision': 'rejected'}, status='refused', reason=stored['reason']).model_dump()
    return changed

async def record(state: AgentState):
    changed = step(state, 'record')
    proposal = state['proposal']['answer']
    result = await gateway.tool('record_decision', {'rid': state['rid'], 'identity': proposal['id'], 'version': proposal['version'], 'payload_hash': proposal['payload_hash']})
    changed['decision'] = result
    if result['status'] != 'ok':
        changed['response'] = result
    return changed

async def replay(state: AgentState):
    changed = step(state, 'replay')
    result = detect.run_rules(state['rid'], state['profile'], state['source_id'], state['rule_id'])
    if result.status != 'ok':
        changed['response'] = reply(state['rid'], {'decision': state['decision']['answer']}, status=result.status, reason='결정은 기록됐지만 재생은 완료되지 않았습니다: ' + result.reason).model_dump(mode='json')
        return changed
    changed['response'] = reply(state['rid'], {'decision': state['decision']['answer'], 'after': result.answer, 'comparison_scope': '동일하게 저장한 입력의 규칙 재생', 'quality_improved': '미판정'}, evidence=state['documents']['evidence'], meta={'warnings': ['통지 수의 변화는 품질 개선의 증거가 아닙니다']}).model_dump(mode='json')
    return changed

def graph(checkpointer):
    builder = StateGraph(AgentState)
    for name, node in [('observe', observe), ('relate', relate), ('retrieve', retrieve), ('propose', propose), ('approval', await_approval), ('record', record), ('replay', replay)]:
        builder.add_node(name, node)
    builder.add_edge(START, 'observe')
    for current, following in [('observe', 'relate'), ('relate', 'retrieve'), ('retrieve', 'propose'), ('propose', 'approval'), ('approval', 'record'), ('record', 'replay')]:
        builder.add_conditional_edges(current, lambda state: 'stop' if state.get('response') else 'next', {'stop': END, 'next': following})
    builder.add_edge('replay', END)
    return builder.compile(checkpointer=checkpointer)

async def run(rid: str, inputs: dict, thread_id: str | None=None, resume_proposal: str | None=None):
    thread_id = thread_id or str(uuid4())
    config = {'configurable': {'thread_id': thread_id}, 'recursion_limit': settings()['agent']['max_steps'] + 2}
    async with AsyncPostgresSaver.from_conn_string(env('DATABASE_URL')) as saver:
        workflow = graph(saver)
        if resume_proposal:
            snapshot = await workflow.aget_state(config)
            if not snapshot.next:
                raise ValueError('재개할 승인 대기 작업이 없습니다')
            result = await workflow.ainvoke(Command(resume={'proposal_id': resume_proposal}), config)
        else:
            old = await workflow.aget_state(config)
            if old.values:
                raise ValueError('기존 작업 번호를 새 실행으로 덮지 않습니다')
            result = await workflow.ainvoke({**inputs, 'rid': rid, 'steps': 0, 'visited': []}, config)
    if result.get('__interrupt__'):
        return reply(rid, {'thread_id': thread_id, 'proposal': result['proposal']['answer'], 'draft_set': result.get('draft_set')}, status='pending_approval', reason='사람의 결정이 저장된 뒤 이어집니다', meta=result.get('model_meta'))
    response = result.get('response')
    if response is None:
        raise ValueError('에이전트 종료 결과가 없습니다')
    response['meta']['thread_id'] = thread_id
    response['meta']['origin_rid'] = result['rid']
    response['meta']['draft_id'] = result.get('draft_set', {}).get('id')
    if result.get('model_meta'):
        response['meta']['agent_model'] = result['model_meta']
    response['rid'] = rid
    return response

def route_question(rid: str, profile: str, source_ids: list[str], question: str, provider: str, context: dict | None=None, graph_start: str | None=None, graph_end: str | None=None, verify: bool=True, context_level: str='probed'):
    selected, meta = gateway.route(provider, question, context)
    route = selected['route']
    if route == 'table':
        result = data.question(rid, profile, source_ids, question, provider, context, verify, context_level)
    elif route == 'document':
        result = rag.ask(rid, profile, question, provider, context)
    elif route == 'graph' and graph_start and graph_end:
        result = ontology.path(rid, graph_start, graph_end)
    else:
        result = reply(rid, status='insufficient', reason=selected['reason'] or '질문 대상이 부족합니다')
    result.meta['router'] = meta
    result.meta['route'] = route
    return result

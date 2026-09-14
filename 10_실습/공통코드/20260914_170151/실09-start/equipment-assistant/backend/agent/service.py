"""Incremental workflow nodes, explicit approval interrupt and bounded replay."""
from backend.common.response import reply
from backend.data import service as data
from backend.ontology import service as ontology
from backend.rag import service as rag
from . import gateway

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

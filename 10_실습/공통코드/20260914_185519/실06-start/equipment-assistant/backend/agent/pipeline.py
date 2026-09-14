"""First workflow node chain: explicit stage contracts without approval or LLM routing."""
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from backend.common.response import reply
from backend.data.service import upload
from backend.detect.service import run_rules
from backend.ontology.gateway import flush_outbox


class PipelineState(TypedDict,total=False):
    rid:str
    profile:str
    source_id:str
    rule_id:str
    ingest:dict
    detection:dict
    projection:dict
    prediction:dict
    prediction_request:dict
    response:dict


def stopped(state, stage, exc):
    known = isinstance(exc, (ValueError, FileNotFoundError, ImportError))
    reason = str(exc) if known else type(exc).__name__
    completed = {key: state[key] for key in ('ingest','detection','prediction') if key in state}
    return {'response': reply(state['rid'], {'stopped_at':stage,'completed':completed},
        status='insufficient' if known else 'failed', reason=stage+' 단계 중단: '+reason,
        meta={'warnings':['앞서 저장된 결과는 유지됩니다. 자동 롤백을 수행하지 않았습니다'],
              'stage':stage,'failure_type':type(exc).__name__}).model_dump(mode='json')}


def checked(state, name, response):
    output = response.model_dump(mode='json')
    result = {name:output}
    if response.status != 'ok':
        completed = {key: state[key] for key in ('ingest','detection','prediction') if key in state}
        result['response'] = reply(state['rid'], {'stopped_at':name,'completed':completed,'stage_result':output},
            status=response.status, reason=name+' 단계 중단: '+response.reason).model_dump(mode='json')
    return result


def ingest(state):
    try:
        return checked(state,'ingest',upload(state['rid'],state['profile'],state['source_id']))
    except Exception as exc:
        return stopped(state,'ingest',exc)


def detect(state):
    try:
        return checked(state,'detection',run_rules(state['rid'],state['profile'],state['source_id'],state['rule_id']))
    except Exception as exc:
        return stopped(state,'detection',exc)


def project(state):
    try:
        result=flush_outbox()
        status=result.get('status')
        if status not in {'not_applicable','pending','synchronized'}:
            raise RuntimeError('unknown projection state')
        warnings=([result['reason']] if status=='not_applicable' else
                  ['그래프 반영이 남았습니다'] if status=='pending' else [])
        return {'projection':result,'response':reply(state['rid'],{
            'ingest':state['ingest']['answer'],'detect':state['detection']['answer'],
            'prediction':state.get('prediction'),'graph':result,
            'scope':{'ingest':'completed','detection':'completed',
                     'prediction':'completed' if state.get('prediction_request') else 'not_requested',
                     'projection':status}},meta={'warnings':warnings}).model_dump(mode='json')}
    except Exception as exc:
        return stopped(state,'projection',exc)


def predict(state):
    request=state.get('prediction_request')
    if not request:return {}
    try:
        from backend.detect.model_gateway import job
        result=job(state['profile'],state['source_id'],request['method'],request['parameters'])
        return {'prediction':result}
    except Exception as exc:
        return stopped(state,'prediction',exc)


def run(rid,profile,source_id,rule_id,prediction_request=None):
    workflow=StateGraph(PipelineState)
    workflow.add_node('ingest',ingest);workflow.add_node('detect',detect);workflow.add_node('predict',predict);workflow.add_node('project',project)
    workflow.add_edge(START,'ingest')
    workflow.add_conditional_edges('ingest',lambda state:'stop' if state.get('response') else 'next',{'stop':END,'next':'detect'})
    workflow.add_conditional_edges('detect',lambda state:'stop' if state.get('response') else 'next',{'stop':END,'next':'predict'})
    workflow.add_conditional_edges('predict',lambda state:'stop' if state.get('response') else 'next',{'stop':END,'next':'project'})
    workflow.add_edge('project',END)
    result=workflow.compile().invoke({'rid':rid,'profile':profile,'source_id':source_id,'rule_id':rule_id,
                                    'prediction_request':prediction_request})
    return result['response']

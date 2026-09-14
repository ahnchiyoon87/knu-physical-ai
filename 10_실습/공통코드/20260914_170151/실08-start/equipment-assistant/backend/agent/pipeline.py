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


def ingest(state):
    response=upload(state['rid'],state['profile'],state['source_id'])
    return {'ingest':response.model_dump(mode='json'),**({'response':response.model_dump(mode='json')} if response.status!='ok' else {})}


def detect(state):
    response=run_rules(state['rid'],state['profile'],state['source_id'],state['rule_id'])
    return {'detection':response.model_dump(mode='json'),**({'response':response.model_dump(mode='json')} if response.status!='ok' else {})}


def project(state):
    result=flush_outbox()
    return {'projection':result,'response':reply(state['rid'],{'ingest':state['ingest']['answer'],
        'detect':state['detection']['answer'],'prediction':state.get('prediction'),'graph':result,
        'scope':'적재·규칙 감지·요청한 CPU 예측·관계 반영' if state.get('prediction_request') else '적재·규칙 감지·관계 반영. 이번 요청에서 예측은 선택하지 않음'},
        meta={'warnings':['그래프 반영이 남았습니다'] if result.get('remaining') else []}).model_dump(mode='json')}


def predict(state):
    request=state.get('prediction_request')
    if not request:return {}
    from backend.detect.model_gateway import job
    try:
        result=job(state['profile'],state['source_id'],request['method'],request['parameters'])
    except (ValueError,FileNotFoundError,ImportError) as exc:
        return {'response':reply(state['rid'],{'ingest':state['ingest'],'detection':state['detection']},
            status='insufficient',reason='감지는 완료됐지만 예측 입력·의존성이 부족합니다: '+str(exc)).model_dump(mode='json')}
    return {'prediction':result}


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

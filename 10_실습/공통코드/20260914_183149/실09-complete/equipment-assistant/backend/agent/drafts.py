"""Persist grounded review drafts; never label generated text as an executed action."""
from uuid import uuid4
from psycopg.types.json import Jsonb
from backend.common.gateway import database
from backend.common.response import reply

KINDS={'condition_change','first_inspection','four_m'}


def save(state,candidate):
    drafts=candidate.get('drafts',[]);evidence=state['documents']['evidence']
    if len(drafts)!=3 or {item.get('kind') for item in drafts}!=KINDS:
        raise ValueError('제안 세 종류가 누락되거나 중복됐습니다')
    for item in drafts:
        ids=item.get('evidence_ids',[])
        if any(type(i)is not int or not 0<=i<len(evidence) for i in ids):raise ValueError('초안의 근거 번호 오류')
        if item['text'].strip() and not ids:raise ValueError('근거 없는 초안 본문입니다')
        item['status']='draft' if item['text'].strip() else 'insufficient'
    identity=str(uuid4())
    result={'id':identity,'profile':state['profile'],'source_id':state['source_id'],
        'lot_id':state.get('lot_id'),'question':state['question'],'drafts':drafts,'evidence':evidence,
        'paths':state.get('paths',{}),'event_ids':[row['id'] for row in state['events']['answer']['rows']],
        'status':'draft','scope':'검토용 문안. 실제 검사·4M 제출·설비 변경을 수행하지 않음'}
    with database() as db:
        db.execute("INSERT INTO lab.artifacts(id,kind,payload) VALUES(%s,'agent_draft',%s)",(identity,Jsonb(result)))
    return result


def read(rid,identity,kind=None):
    if kind and kind not in KINDS:raise ValueError('초안 종류를 확인하세요')
    with database(readonly=True) as db:
        row=db.execute("SELECT payload FROM lab.artifacts WHERE id=%s AND kind='agent_draft'",(identity,)).fetchone()
    if not row:return reply(rid,status='none',reason='저장된 초안이 없습니다')
    payload=dict(row['payload'])
    if kind:payload['drafts']=[item for item in payload['drafts'] if item['kind']==kind]
    return reply(rid,payload,evidence=payload['evidence'])


def eight_d(rid,identity):
    source=read(rid,identity)
    if source.status!='ok':return source
    draft=source.answer
    with database(readonly=True) as db:
        decisions=db.execute("SELECT p.id,p.payload,p.actor,p.reason,d.before_rule,d.after_rule "
            "FROM lab.proposals p JOIN lab.decisions d ON d.proposal_id=p.id "
            "WHERE p.status='recorded' AND p.payload->>'profile'=%s AND p.payload->>'source_id'=%s "
            "AND p.payload->'event_ids' ?| %s::text[]",(draft['profile'],draft['source_id'],draft['event_ids'])).fetchall()
    sections=[
        {'step':'D1','title':'팀 구성','status':'unconfirmed','content':'실제 참여자·역할을 확인해 작성합니다'},
        {'step':'D2','title':'문제 정의','status':'observed','content':{'lot_id':draft['lot_id'],'event_ids':draft['event_ids']}},
        {'step':'D3','title':'임시 봉쇄','status':'draft','content':[d for d in draft['drafts'] if d['kind']=='first_inspection']},
        {'step':'D4','title':'원인 검증','status':'unconfirmed','content':'관계·문서 근거는 아래에 있습니다. 확정 원인에는 실제 점검 증거가 더 필요합니다'},
        {'step':'D5','title':'시정책 선택·검증','status':'recorded' if decisions else 'draft','content':decisions or draft['drafts']},
        {'step':'D6','title':'실행·효과 확인','status':'partial' if decisions else 'unconfirmed','content':{'software_rule_changes':decisions,'physical_effect':'미확인'}},
        {'step':'D7','title':'재발 방지','status':'unconfirmed','content':'효과 검증 뒤 문서·규칙에 반영할 항목을 정합니다'},
        {'step':'D8','title':'기여 인정','status':'unconfirmed','content':'실제 참여와 완료 범위에 맞춰 작성합니다'}]
    return reply(rid,{'draft_id':identity,'sections':sections,'scope':'8D 검토 초안. 미확인 칸을 완료로 채우지 않음'},evidence=draft['evidence'])

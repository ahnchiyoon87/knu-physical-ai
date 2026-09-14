"""Small boundary checks; no DB, model or end-to-end execution."""
import pytest
from backend.common.response import reply
from backend.data.service import question
from backend.eval.service import validate_cases
from backend.agent import service


def test_changed_source_does_not_reuse_previous_sql():
    with pytest.raises(ValueError,match='이전 대화'):
        question('test','synthetic',['shots'],'평균','api',{'profile':'transfer','source_ids':['loans']})


def test_unwritten_question_set_stops_before_calls():
    with pytest.raises(ValueError,match='먼저 작성'):
        validate_cases([{'id':'Q01','question':'','expected_documents':[],'expected_statuses':[]}])


def test_ragas_requires_human_reference_before_calls():
    case={'id':'Q01','question':'확인 항목은?','expected_documents':['SHIFT'],'expected_statuses':['ok']}
    with pytest.raises(ValueError,match='reference'):
        validate_cases([case],require_reference=True)
    validate_cases([{**case,'reference':'점검 시점과 설비, 항목, 관측 결과를 기록한다.'}],require_reference=True)


def test_replay_failure_does_not_erase_recorded_decision(monkeypatch):
    import asyncio
    monkeypatch.setattr(service.detect,'run_rules',lambda *args:reply('test',status='insufficient',reason='입력 없음'))
    result=asyncio.run(service.replay({'rid':'test','profile':'synthetic','source_id':'shots','rule_id':'r',
        'decision':{'answer':{'id':'recorded'}},'steps':5,'visited':[]}))['response']
    assert result['status']=='insufficient'
    assert result['answer']['decision']=={'id':'recorded'}


def test_relative_percent_does_not_use_standard_deviation():
    from backend.detect.rules import detect_rows
    rows=[{'lot_id':'a','row_no':i,'value':v} for i,v in enumerate([10,10,10.3])]
    result=detect_rows(rows,{'mode':'relative','relative_unit':'percent','width':2.5,'baseline_count':2,'version':1})
    assert [row['row_no'] for row in result]==[2]
    with pytest.raises(ValueError,match='평균 0'):
        detect_rows([{'lot_id':'a','row_no':i,'value':v} for i,v in enumerate([0,0,1])],
                    {'mode':'relative','relative_unit':'percent','width':2.5,'baseline_count':2,'version':1})


def test_multichannel_requires_both_directions_and_preserves_suppression():
    from backend.detect.rules import detect_rows
    values=[(10,20),(10,20),(11,20),(11,18),(11,18)]
    rows=[{'lot_id':'a','row_no':i,'value':a,'channels':{'22':a,'18':b}} for i,(a,b) in enumerate(values)]
    result=detect_rows(rows,{'mode':'multichannel','operator':'and','baseline_count':2,'version':1,'suppression_shots':2,
        'conditions':[{'column_id':22,'direction':'above','percent':5},{'column_id':18,'direction':'below','percent':5}]})
    assert [row['row_no'] for row in result]==[3,4]
    assert [row['suppressed'] for row in result]==[False,True]


def test_absolute_uses_per_lot_reference_bounds():
    from backend.detect.rules import detect_rows
    rows=[{'lot_id':'a','row_no':1,'value':11,'lower':9,'upper':12},
          {'lot_id':'b','row_no':2,'value':11,'lower':6,'upper':9}]
    result=detect_rows(rows,{'mode':'absolute','version':1})
    assert [row['lot_id'] for row in result]==['b']


def test_missing_graph_target_stops_before_document_or_model_calls():
    import asyncio
    result=asyncio.run(service.relate({'rid':'test','profile':'synthetic','source_id':'shots','steps':1,'visited':['observe']}))
    assert result['response']['status']=='insufficient'


def test_forecast_holdout_excludes_answers_from_model_input(monkeypatch):
    from backend.detect import models
    seen=[]
    def prediction(values,horizon):
        seen.extend(values)
        return {'median':[5,6],'lower':[4,5],'upper':[6,7]}
    monkeypatch.setattr(models,'chronos_forecast',prediction)
    result=models.forecast_evaluation([1,2,3,4,5,6],2,True)
    assert seen==[1,2,3,4]
    assert result['expected']==[5,6]
    assert result['metrics']['median_mae']==0
    assert result['metrics']['last_value_mae']==1.5

import pytest
from backend.detect.rules import detect_rows
from backend.detect.provenance import bind_series_scores
from backend.agent import pipeline
from backend.common.response import reply


def rows():
    return [{"row_no":i+1,"lot_id":"4","value":v} for i,v in enumerate([10.,10.,None,12.])]


def test_absolute_and_relative_denominators():
    absolute={};relative={}
    detect_rows(rows(),{"mode":"absolute","lower":0,"upper":11,"version":1},absolute)
    detect_rows(rows(),{"mode":"relative","baseline_count":2,"width":2.5,"relative_unit":"percent","version":1},relative)
    assert absolute=={"input_rows":4,"baseline_rows":0,"missing_rows":1,"evaluated":3}
    assert relative=={"input_rows":4,"baseline_rows":2,"missing_rows":1,"evaluated":1}


def test_series_scores_keep_original_rows():
    source=[{"row_no":n,"lot_id":"4","value":1.} for n in [241,242,243,244]]
    result=bind_series_scores({"baseline_count":2,"scores":[.8,.2],"predictions":[1,0]},source,"p","s")
    assert [r['row_no'] for r in result['observations']]==[243,244]
    assert result['observations'][0]['row_id']=='p:s:row:243'
    assert result['test_rows']==2
    with pytest.raises(ValueError):
        bind_series_scores({"baseline_count":2,"scores":[.8],"predictions":[1,0]},source,"p","s")


@pytest.mark.parametrize('fail_at',['ingest','detection','prediction','projection'])
def test_pipeline_stops_and_preserves_completed_stages(monkeypatch,fail_at):
    from backend.detect import model_gateway
    calls=[]
    def operation(name,value):
        def call(*args,**kwargs):
            calls.append(name)
            if name==fail_at:raise RuntimeError('sensitive-example-must-not-leak')
            return value
        return call
    monkeypatch.setattr(pipeline,'upload',operation('ingest',reply('r',{'rows':10})))
    monkeypatch.setattr(pipeline,'run_rules',operation('detection',reply('r',{'flagged':0})))
    monkeypatch.setattr(model_gateway,'job',operation('prediction',{'scores':[]}))
    monkeypatch.setattr(pipeline,'flush_outbox',operation('projection',{'status':'synchronized','remaining':0}))
    response=pipeline.run('r','p','s','rule',{'method':'pyod','parameters':{}})
    order=['ingest','detection','prediction','projection']
    assert calls==order[:order.index(fail_at)+1]
    assert response['status']=='failed'
    assert response['answer']['stopped_at']==fail_at
    assert set(response['answer']['completed'])==set(order[:order.index(fail_at)])
    assert 'sensitive-example' not in str(response)


def test_csv_projection_is_not_reported_as_db_sync(monkeypatch):
    monkeypatch.setattr(pipeline,'upload',lambda *args:reply('r',{'rows':10}))
    monkeypatch.setattr(pipeline,'run_rules',lambda *args:reply('r',{'flagged':0}))
    monkeypatch.setattr(pipeline,'flush_outbox',lambda:{'status':'not_applicable','remaining':None,'reason':'CSV 관계표 단계'})
    result=pipeline.run('r','p','s','rule')
    assert result['answer']['scope']['projection']=='not_applicable'
    assert result['answer']['scope']['prediction']=='not_requested'
    assert result['meta']['warnings']==['CSV 관계표 단계']


def test_non_ok_response_stops_before_detection(monkeypatch):
    monkeypatch.setattr(pipeline,'upload',lambda *args:reply('r',status='insufficient',reason='입력 없음'))
    monkeypatch.setattr(pipeline,'run_rules',lambda *args:pytest.fail('must not detect'))
    result=pipeline.run('r','p','s','rule')
    assert result['status']=='insufficient'
    assert result['answer']['stopped_at']=='ingest'


def test_no_rows_after_baseline_is_insufficient(monkeypatch):
    from backend.detect import service
    definition={'profile':'p','source_id':'s','mode':'relative','column_id':22,'baseline_count':2,'width':2.5,'relative_unit':'percent'}
    monkeypatch.setattr(service.gateway,'rule',lambda _: {'definition':definition,'version':1})
    monkeypatch.setattr(service.gateway,'rule_rows',lambda *args:[{'row_no':1,'lot_id':'a','value':10.},{'row_no':2,'lot_id':'a','value':10.}])
    monkeypatch.setattr(service.gateway,'save_events',lambda *args:pytest.fail('no valid evaluation'))
    result=service.run_rules('r','p','s','rule')
    assert result.status=='insufficient'
    assert result.answer['evaluated']==0
    assert result.answer['baseline_rows']==2

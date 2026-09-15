"""Neo4j Browser에서 읽기 질의를 실행하고 실제 결과 화면을 저장한다."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
work=root/'작업기록/셋째날제작_20260915/Browser실제화면/현재'
work.mkdir(exist_ok=False)
queries=[
('관계그래프', "MATCH p=(sop:SOP)-[:APPLIES_TO]->(a:Asset)-[:HAS_SENSOR]->(s:Sensor) WHERE sop.status = 'active' RETURN p"),
('설비와SOP', "MATCH (a:Asset) OPTIONAL MATCH (sop:SOP)-[:APPLIES_TO]->(a) WHERE sop.status = 'active' AND sop.event_type = 'COOLING_ANOMALY' RETURN a.asset_id AS asset_id, a.name AS asset_name, sop.sop_key AS active_sop ORDER BY asset_id, active_sop"),
('센서식별자', "MATCH (a:Asset {asset_id:'HYD-01'})-[:HAS_SENSOR]->(s:Sensor) RETURN a.asset_id AS asset_id, s.sensor_id AS graph_sensor_id, s.code AS observation_sensor_code, s.unit AS unit, labels(s) AS labels ORDER BY s.code")]
records=[]
with sync_playwright() as engine:
    browser=engine.chromium.launch_persistent_context(str(root/'.runtime/neo4j-review-browser'),headless=True,
                                                    viewport={'width':1600,'height':1000},device_scale_factor=1.5)
    try:
        page=browser.pages[0]
        page.goto('http://localhost:57474/browser/',wait_until='networkidle')
        page.locator('input[name=hostname]').fill('localhost:57687')
        page.get_by_role('combobox').click()
        page.get_by_role('option',name='bolt://',exact=True).click()
        page.locator('input[name=username]').fill('neo4j')
        page.locator('input[name=password]').fill('hydops-lecture')
        page.get_by_role('button',name='Connect',exact=True).click()
        page.locator('input[name=password]').wait_for(state='hidden',timeout=15000)
        page.get_by_text('Loading...',exact=True).first.wait_for(state='hidden',timeout=15000)
        for name,query in queries:
            editor=page.get_by_role('textbox',name='Cypher Editor')
            editor.fill(query)
            editor.press('Escape')
            page.get_by_role('button',name='Run',exact=True).first.click()
            if name=='관계그래프':
                page.get_by_text('Results overview',exact=True).first.wait_for(timeout=15000)
            else:
                page.get_by_text('active_sop' if name=='설비와SOP' else 'graph_sensor_id',exact=True).last.wait_for(timeout=15000)
            page.get_by_role('button',name='Expand frame',exact=True).first.click()
            if name=='관계그래프':
                page.get_by_role('button',name='Zoom to fit',exact=True).click()
            page.screenshot(path=str(work/(name+'.png')))
            body=page.locator('body').inner_text()
            records.append({'name':name,'query':query,'visible_text':body})
            print(name, 'captured')
            # Fullscreen frame has a restore control whose label is inspected at runtime.
            controls=page.get_by_role('button').evaluate_all('(es)=>es.map(e=>({aria:e.getAttribute("aria-label"),title:e.title,text:e.innerText}))')
            (work/(name+'_조작.json')).write_text(json.dumps(controls,ensure_ascii=False,indent=2),encoding='utf-8')
            if name!=queries[-1][0]:
                page.get_by_role('button',name='Shrink frame',exact=True).first.click()
        (work/'조회기록.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        browser.close()

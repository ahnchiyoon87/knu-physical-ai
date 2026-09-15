"""실행된 둘째 날 검토 노트북을 실제 JupyterLab에서 열어 출력 영역을 캡처한다."""
from pathlib import Path
from urllib.parse import quote
import json
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
work=root/'작업기록/첫날제작_20260915/노트북실제화면_v1/둘째날품질조회'
output=work/'캡처'
output.mkdir(exist_ok=False)
token=(root/'.runtime/notebook-review-token').read_text(encoding='utf-8')
plans=[('원본과 오류 주입 복사본','원본과주입'),('품질 표시와 DB에 남은 값','품질표'),
       ('같은 실행에서 구간별 판단','구간판단'),('결측 샘플의 1초 집계','결측집계'),
       ('냉각 변화와 센서 고착','설비와센서')]
with sync_playwright() as engine:
    browser=engine.chromium.launch()
    try:
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=2)
        errors=[]
        page.on('pageerror',lambda error:errors.append(type(error).__name__))
        page.goto('http://localhost:8889/lab/tree/'+quote('둘째날품질조회/품질_결과.ipynb')+'?token='+token,wait_until='domcontentloaded')
        page.get_by_role('heading',name='품질 표시와 판단할 값',exact=True).wait_for(timeout=30000)
        for text,name in plans:
            cell=page.locator('.jp-Notebook .jp-CodeCell').filter(has_text=text)
            cell.scroll_into_view_if_needed()
            cell.locator('.jp-OutputArea').screenshot(path=str(output/(name+'.png')))
        (output/'검토정보.json').write_text(json.dumps({'images':[p[1]+'.png' for p in plans],
             'javascript_errors':errors,'scope':'실제로 실행·저장된 노트북의 출력 영역. 학생 코딩 에이전트 완주 아님.'},ensure_ascii=False,indent=2),encoding='utf-8')
        print('실제 JupyterLab 출력 영역5장 캡처, JS오류',len(errors))
    finally:
        browser.close()

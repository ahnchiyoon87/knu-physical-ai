from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
work=root/'작업기록/첫날제작_20260915/노트북실제화면_v1/실전조회'
token=(root/'.runtime/notebook-review-token').read_text(encoding='utf-8')
with sync_playwright() as engine:
    browser=engine.chromium.launch()
    try:
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=2)
        page.goto('http://localhost:8889/lab/tree/'+quote('실전조회/DB조회_결과.ipynb')+'?token='+token,wait_until='domcontentloaded')
        page.get_by_role('heading',name='실행 구간과 원본 사이클 확인',exact=True).wait_for(timeout=30000)
        for text,name in [('마지막 60초 조회','최근60초'),('사이클 경계의 60초 조회','사이클경계'),('압력 첫1초의 원본과 집계 비교','압력집계')]:
            cell=page.locator('.jp-Notebook .jp-CodeCell').filter(has_text=text)
            cell.scroll_into_view_if_needed()
            area=cell.locator('.jp-OutputArea')
            if name=='사이클경계':
                area.locator('.jp-OutputArea-child').nth(1).screenshot(path=str(work/'사이클경계_표.png'))
            else:
                area.screenshot(path=str(work/(name+'.png')))
        print('Actual notebook output areas captured: 3')
    finally:
        browser.close()

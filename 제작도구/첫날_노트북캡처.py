from pathlib import Path
from urllib.parse import quote
import json
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
work=root/'작업기록/첫날제작_20260915/노트북실제화면_v1'
token=(root/'.runtime/notebook-review-token').read_text(encoding='utf-8')
with sync_playwright() as engine:
    browser=engine.chromium.launch()
    try:
        page=browser.new_page(viewport={'width':1536,'height':1000})
        diagnostics=[]
        page.on('pageerror',lambda error:diagnostics.append(str(error).replace(token,'[redacted]')))
        page.on('requestfailed',lambda request:diagnostics.append(request.url.split('?')[0]+' '+str(request.failure)))
        page.goto('http://localhost:8889/lab/tree/'+quote('관측_실행결과.ipynb')+'?token='+token,wait_until='domcontentloaded')
        try:
            page.locator('.jp-Notebook .jp-Cell').first.wait_for(timeout=15000)
            page.get_by_role('heading',name='통합반 1회 · 센서와 데이터 흐름 알아보기 (제공 노트북)',exact=True).wait_for(timeout=30000)
        except Exception:
            (work/'브라우저오류.json').write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding='utf-8')
            page.screenshot(path=str(work/'UI진단.png'))
            (work/'UI진단.txt').write_text(page.locator('body').inner_text(),encoding='utf-8')
            raise
        if page.get_by_role('button',name='No',exact=True).is_visible():
            page.get_by_role('button',name='No',exact=True).click()
        page.get_by_text('Would you like to get notified about official Jupyter news?',exact=True).wait_for(state='hidden')
        page.locator('.jp-NotebookPanel').screenshot(path=str(work/'노트북_본문.png'))
        for text, filename in [('원본 파일의 모양','원본_열수.png'),('공통 관측 레코드 한 줄','관측_한값.png'),('저장본 남기기 — saved/','저장_결과.png')]:
            cell=page.locator('.jp-Notebook .jp-CodeCell').filter(has_text=text)
            cell.scroll_into_view_if_needed()
            cell.locator('.jp-OutputArea').wait_for()
            cell.screenshot(path=str(work/filename.replace('.png','_v3.png')))
        (work/'UI본문.txt').write_text(page.locator('body').inner_text(),encoding='utf-8')
        print('Visible notebook cells:',page.locator('.jp-Notebook .jp-Cell').count())
    finally:
        browser.close()

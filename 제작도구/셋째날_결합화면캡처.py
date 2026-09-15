"""실행된 셋째 날 검토 노트북을 실제 JupyterLab에서 열어 출력 영역을 캡처한다."""
from pathlib import Path
from urllib.parse import quote
import json
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
work=root/'작업기록/첫날제작_20260915/노트북실제화면_v1/셋째날관계조회'
output=work/'캡처'
output.mkdir(exist_ok=False)
token=(root/'.runtime/notebook-review-token').read_text(encoding='utf-8')
plans=[('사건이 인용한 문서의 판과 절','사건인용'),('같은 ID와 잘못된 ID의 차이','ID되돌리기'),
       ('그래프의 센서와 DB의 최근 관측 연결','관계와최근값'),('결과 파일 다시 열기와 내 임시 실행 정리','저장과정리')]
with sync_playwright() as engine:
    browser=engine.chromium.launch()
    try:
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=2)
        errors=[]
        page.on('pageerror',lambda error:errors.append(type(error).__name__))
        page.goto('http://localhost:8889/lab/tree/'+quote('셋째날관계조회/관계_결과.ipynb')+'?token='+token,wait_until='domcontentloaded')
        page.get_by_role('heading',name='관계와 측정값을 함께 확인하기',exact=True).wait_for(timeout=30000)
        for text,name in plans:
            cell=page.locator('.jp-Notebook .jp-CodeCell').filter(has_text=text)
            cell.scroll_into_view_if_needed()
            cell.locator('.jp-OutputArea').screenshot(path=str(output/(name+'.png')))
        (output/'검토정보.json').write_text(json.dumps({'images':[p[1]+'.png' for p in plans],
             'javascript_errors':errors,'scope':'실제로 실행·저장된 노트북의 출력 영역. 학생 코딩 에이전트 완주 아님.'},ensure_ascii=False,indent=2),encoding='utf-8')
        print('실제 JupyterLab 출력 영역4장 캡처, JS오류',len(errors))
    finally:
        browser.close()

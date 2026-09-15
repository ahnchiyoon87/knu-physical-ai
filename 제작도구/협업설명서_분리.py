from pathlib import Path
import re
import json
import pymupdf
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
folder = root / '강의계획과운영/운영안'
# 최초 분리 이력 재현용. 현행 출력은 협업설명서_출력.py를 사용한다.
source = root / '작업기록/협업설명서_20260915/분리전_통합본/시나리오와AI운영_협업설명서.html'
html = source.read_text(encoding='utf-8')
head = html.split('<section class="page">')[0]
sections = re.findall(r'<section class="page">.*?</section>', html, re.S)
assert len(sections) == 4
review = root / '작업기록/협업설명서_20260915/분리검토'
review.mkdir(exist_ok=False)
plans = [('냉각이상대응_시나리오설명서', sections[:2]), ('코딩에이전트와LiteLLM_운영설명서', sections[2:])]
with sync_playwright() as engine:
    browser = engine.chromium.launch()
    try:
        for name, pages in plans:
            target = folder / (name + '.html')
            pdf = target.with_suffix('.pdf')
            assert not target.exists() and not pdf.exists()
            text = head.replace('제조 피지컬 AI · 시나리오와 AI 운영', name.replace('_', ' · '))
            for i, section in enumerate(pages, 1):
                section = re.sub(r'\d / 4', f'{i} / 2', section)
                if name.startswith('코딩'):
                    section = section.replace('03 / 로컬 실행과 중앙 AI 중계', '01 / 코딩 에이전트와 중앙 AI 중계').replace('04 / GCP 배포와 운영 준비', '02 / GCP 배포와 운영 준비')
                    section = section.replace('LiteLLM은 모델 API로 가는 요청을 중계하고 학생별 접근·사용량을 관리하는 관문입니다.', '코딩 에이전트는 학생 PC에서 파일 수정·명령 실행을 돕고, LiteLLM은 모델 요청과 학생별 접근·사용량을 중계·관리합니다.')
                text += section
            target.write_text(text + '</html>', encoding='utf-8')
            page = browser.new_page()
            page.goto(target.as_uri())
            page.emulate_media(media='print')
            page.evaluate('document.fonts.ready')
            overlaps = page.locator('.page').evaluate_all('(es)=>es.map(e=>{const f=e.querySelector("footer").getBoundingClientRect();return [...e.children].filter(c=>c.tagName!=="FOOTER").some(c=>c.getBoundingClientRect().bottom>f.top-6)})')
            assert not any(overlaps), (name, overlaps)
            page.pdf(path=str(pdf),print_background=True,prefer_css_page_size=True)
            page.close()
            doc = pymupdf.open(pdf)
            assert len(doc) == 2
            for i, pdfpage in enumerate(doc, 1):
                pdfpage.get_pixmap(matrix=pymupdf.Matrix(1.2,1.2)).save(review / f'{name}_{i}.png')
            print(name, len(doc))
    finally:
        browser.close()
(review / '확인.json').write_text(json.dumps({'documents':[p[0] for p in plans], 'pages_each':2,'footer_overlap':False},ensure_ascii=False,indent=2),encoding='utf-8')

from pathlib import Path
import json
import pymupdf as fitz
import argparse
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description='현행 설명서 HTML 하나를 새 폴더에 PDF로 출력')
parser.add_argument('name', choices=['냉각이상대응_시나리오설명서', '코딩에이전트와LiteLLM_운영설명서'])
parser.add_argument('destination', type=Path)
args = parser.parse_args()
source = root / '강의계획과운영/운영안' / (args.name + '.html')
target = args.destination / (args.name + '.pdf')
review = args.destination / '렌더'
if target.exists() or review.exists():
    raise SystemExit('기존 PDF와 검토 폴더를 보존합니다.')
review.mkdir(parents=True)
with sync_playwright() as engine:
    browser = engine.chromium.launch()
    try:
        page = browser.new_page(viewport={'width': 1200, 'height': 900})
        page.goto(source.as_uri())
        page.emulate_media(media='print')
        page.evaluate('document.fonts.ready')
        sizes = page.locator('.page').evaluate_all('(els)=>els.map(e=>({height:e.clientHeight,scroll:e.scrollHeight}))')
        assert all(s['scroll'] <= s['height'] for s in sizes), sizes
        overlaps = page.locator('.page').evaluate_all('(els)=>els.map(e=>{const f=e.querySelector("footer").getBoundingClientRect();return [...e.children].filter(c=>c.tagName!=="FOOTER").some(c=>c.getBoundingClientRect().bottom>f.top-6)})')
        assert not any(overlaps), overlaps
        page.pdf(path=str(target), print_background=True, prefer_css_page_size=True)
    finally:
        browser.close()
doc = fitz.open(target)
assert len(doc) == 2, len(doc)
for index, page in enumerate(doc, 1):
    page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3)).save(review / f'{index}.png')
    assert page.get_text().strip(), index
(review.parent / '출력검사.json').write_text(json.dumps({'pages':len(doc),'layout':sizes,'pdf':target.name},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'PDF {len(doc)} pages: {target}')

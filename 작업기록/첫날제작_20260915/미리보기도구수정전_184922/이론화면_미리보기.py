"""Markdown 이론 덱을 로컬 HTML로 만들고 실제 브라우저 렌더를 검사한다.

PPTX 내보내기나 수업 앱 캡처가 아니다. 기존 결과를 덮지 않는다.
"""
import argparse
import html
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright


def inline(text):
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', text)


def content(lines):
    result, rowset, paragraph = [], [], []
    def flush():
        if paragraph:
            result.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
        if rowset:
            result.append('<table><thead><tr>' + ''.join('<th>'+inline(c)+'</th>' for c in rowset[0]) + '</tr></thead><tbody>')
            for row in rowset[1:]:
                result.append('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>')
            result.append('</tbody></table>')
            rowset.clear()
    for line in lines:
        if line.startswith('|'):
            if paragraph:
                flush()
            cells = [s.strip() for s in line.strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                rowset.append(cells)
        elif not line.strip():
            flush()
        elif line.startswith('#') or line.startswith('```') or line.startswith('- '):
            raise ValueError('이 미리보기 변환기가 지원하지 않는 문법: '+line)
        else:
            if rowset:
                flush()
            paragraph.append(line)
    flush()
    return '\n'.join(result)


def build(source, output):
    if output.exists():
        raise FileExistsError(output)
    text = source.read_text(encoding='utf-8')
    parts = re.split(r'^## (S\d+ .+)$', text, flags=re.M)
    if len(parts) < 3:
        raise ValueError('S번호 제목이 없습니다.')
    slides = []
    for idx in range(1, len(parts), 2):
        code, title = parts[idx].split(' ', 1)
        slides.append(f'<section id="{code}"><h1>{inline(title)}</h1><main>{content(parts[idx+1].splitlines())}</main></section>')
    css = '''*{box-sizing:border-box}html,body{margin:0;background:#ddd;font-family:"Malgun Gothic",sans-serif;color:#162f36}
section{width:1600px;height:900px;padding:70px 86px;background:#faf9f5;overflow:hidden;position:relative;break-after:page}
h1{font-size:62px;line-height:1.2;margin:0 0 40px;font-weight:700;letter-spacing:-1.8px;color:#133b43}
main{font-size:32px;line-height:1.55}p{margin:0 0 27px;word-break:keep-all}strong{color:#007c78}
table{border-collapse:collapse;width:100%;font-size:30px;line-height:1.48;margin:0 0 30px;table-layout:fixed}
th{text-align:left;background:#133b43;color:white;font-weight:600;padding:19px 24px}
td{padding:21px 24px;border-bottom:2px solid #cedad8;vertical-align:top;word-break:keep-all}
code{font-family:Consolas,"Malgun Gothic",monospace;font-size:.92em} @page{size:1600px 900px;margin:0}'''
    output.mkdir(parents=True)
    page_path = output/'slides.html'
    page_path.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>제조 데이터와 판단</title><style>'+css+'</style><body>'+''.join(slides)+'</body></html>', encoding='utf-8')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':1600,'height':900}, device_scale_factor=1)
        page.goto(page_path.resolve().as_uri())
        page.evaluate('document.fonts.ready')
        layouts = []
        for section in page.locator('section').all():
            code = section.get_attribute('id')
            layout = section.evaluate('''el=>{const b=el.getBoundingClientRect();return {id:el.id,overflow:el.scrollHeight>el.clientHeight||el.scrollWidth>el.clientWidth,boxes:[...el.querySelectorAll('h1,p,td,th')].map(x=>{const r=x.getBoundingClientRect();return {text:x.textContent,x:r.x-b.x,y:r.y-b.y,width:r.width,height:r.height,bottom:r.bottom-b.y}})}}''')
            section.screenshot(path=str(output/f'{code}.png'))
            layouts.append(layout)
        browser.close()
    errors = [x['id'] for x in layouts if x['overflow'] or any(b['bottom'] > 860 for b in x['boxes'])]
    (output/'layout.json').write_text(json.dumps({'source':str(source),'scope':'로컬 이론 HTML 브라우저 렌더. 수업 앱 캡처/PPTX 검증 아님.', 'errors':errors,'slides':layouts},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'slides':len(slides),'errors':errors,'output':str(output)},ensure_ascii=False))
    if errors:
        raise RuntimeError('슬라이드 영역을 벗어난 내용: '+','.join(errors))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    build(args.source,args.output)

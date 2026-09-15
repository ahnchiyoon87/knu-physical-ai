"""영상06 본문과 실제 원본 그래프를 렌더한다. 실제 제품 UI가 아니다."""
import argparse
from html import escape
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from 영상02_화면초안 import body_html

ROOT = Path(__file__).resolve().parents[1]


def render_body(body):
    image_match=re.search(r'!\[([^]]+)\]\(([^)]+)\)',body)
    if not image_match:
        return body_html(body)
    alt,path=image_match.groups()
    return '<figure><img src="'+escape(path)+'" alt="'+escape(alt)+'"><figcaption>'+escape(alt)+'</figcaption></figure>'+body_html(body.replace(image_match.group(0),''))


def normalize(text):
    return re.sub(r'\s+', '', text)


def plain_md(body):
    text = re.sub(r'!\[([^]]+)\]\([^)]+\)', r'\1', body)
    lines = []
    for line in text.strip().splitlines():
        if line.startswith('```') or re.match(r'^\|[ :|\-]+\|$', line):
            continue
        lines.append(line.replace('|', '').replace('**', '').replace('`', ''))
    return normalize('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', required=True, help='New evidence folder, relative to project')
    args = parser.parse_args()
    output = (ROOT / args.review).resolve()
    if not output.is_relative_to(ROOT / '작업기록'):
        raise ValueError('Review folder must be under 작업기록')
    output.mkdir(parents=True, exist_ok=False)
    folder = ROOT / '이론자료/1회차/영상06'
    source = folder / '첫값과평균범위_덱.md'
    parts = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    box = lambda s: '<div class="box">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        box('PS1 · 사이클100')+arrow+box('첫1초 · 원본100개')+arrow+box('첫 값147.21bar'),
        '',
        box('입력: 원본100개')+arrow+box('첫 값만 선택')+arrow+box('mean이라는 이름만으로<br>평균 계산을 증명할 수 없음'),
        box('같은 구간의 값 합계')+arrow+box('사용한 개수로 나누기')+arrow+box('평균170.1621bar'),
        box('첫 값147.21bar')+box('평균170.1621bar')+'<div class="tag">같은 원본 · 다른 질문</div>',
        box('최대189.88bar')+arrow+box('차이48.61bar')+arrow+box('최소141.27bar'),
        box('TS1: n=1')+box('FS1: n=10')+box('PS1: n=100')+'<div class="tag">같은1초 · 다른 개수</div>',
        box('1 → 3 → 2 → 4')+box('4 → 2 → 3 → 1')+'<div class="tag">같은 통계 · 다른 순서<br>설명용 숫자 예시</div>',
        box('요약값과 출처')+arrow+box('파일 · 사이클 · 시간 구간')+arrow+box('원본 샘플 다시 읽기'),
        box('단위와 구간부터 확인')+arrow+box('같은 계산 규칙')+arrow+box('센서마다 다른 결과'),
        box('어떤 입력인가?')+arrow+box('몇 개로 계산했나?')+arrow+box('표시와 계산을 구분했나?'),
        box('요약값')+arrow+box('단위 · 설비 · 원본 위치')+arrow+box('다음: 관측 레코드'),
    ]
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.layout{grid-template-columns:530px 1fr;gap:42px}.figure{padding:25px}.body{font-size:27px;line-height:1.5}table{font-size:25px}td,th{padding:11px 13px}.figure:after{content:"설명용 비교 도형"}'
    css += '#s02 .layout{display:block}#s02 .figure{display:none}#s02 .body{width:100%;text-align:center}#s02 img{height:550px;max-width:100%;object-fit:contain}#s02 figcaption{font-size:18px;color:#53657b}#s02 figure{margin:0}#s02 p{font-size:24px;margin:8px 0}#s12 .body{word-break:keep-all}#s10 .layout{grid-template-columns:350px 1fr}#s10 table{font-size:23px}#s10 td,#s10 th{padding:10px 9px}'
    pages = []
    for i, ((heading, body), fig) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">첫 값과 평균·범위</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{fig}</aside><article class="body">{render_body(body)}</article></div><footer><span>같은 구간을 서로 다른 숫자로 설명하기</span><span>{i:02} / 12</span></footer></section>')
    target = folder / '첫값과평균범위_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>첫 값과 평균·범위</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
    records = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':1640, 'height':940})
        page.goto(target.as_uri())
        page.evaluate('document.fonts.ready')
        for i, (_, body) in enumerate(scenes, 1):
            slide = page.locator(f'#s{i:02}')
            check = slide.evaluate('''s=>{const r=s.getBoundingClientRect();let bad=[];for(const e of s.querySelectorAll('article,article p,table,pre,h1,.figure,.box,img,figcaption')){let b=e.getBoundingClientRect();if(b.width===0&&b.height===0)continue;if(b.right>r.right-40||b.bottom>r.bottom-65||b.left<r.left)bad.push(e.textContent.slice(0,40));}return {overflow:bad,text:s.querySelector('article').innerText}}''')
            slide.screenshot(path=str(output/f'S{i:02}.png'))
            assert not check['overflow'], (i, check)
            assert normalize(check['text']) == plain_md(body), (i, 'MD content mismatch')
            records.append({'scene':i, 'overflow':[], 'body_matches_md':True, 'body_text':check['text']})
        browser.close()
    assert normalize(records[9]['body_text']) != plain_md(scenes[9][1].replace('170.1621', '147.21'))
    (output/'렌더검사.json').write_text(json.dumps({'scenes':records, 'changed_mean_rejected':True, 'scope':'HTML 레이아웃·본문대조. 실제20분·PPTX·학생이해 미검증.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

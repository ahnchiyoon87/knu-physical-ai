"""영상08 전체 본문과 재생 시간 개념도를 렌더한다. 실제 제품 UI가 아니다."""
import argparse
from html import escape
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from 영상02_화면초안 import body_html

ROOT = Path(__file__).resolve().parents[1]


def normalize(text):
    return re.sub(r'\s+', '', text)


def plain_md(body):
    lines = []
    for line in body.strip().splitlines():
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
    folder = ROOT / '이론자료/1회차/영상08'
    source = folder / '재생시각과실행_덱.md'
    parts = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    box = lambda s: '<div class="box">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        box('사이클100 · 60초')+arrow+box('사이클101 · 다음60초')+arrow+box('사이클102 · 다음60초'),
        box('재생 기준 시각')+arrow+box('2026-09-01 00:00:00 UTC')+arrow+box('실제 수집 날짜와 구분'),
        box('시각 datetime')+arrow+box('시간 길이 timedelta')+arrow+box('시각 + 60초 = 다음 시작'),
        box('첫 번째: +0초')+arrow+box('두 번째: +60초')+arrow+box('세 번째: +120초'),
        box('100번 / 59초 → 00:00:59')+arrow+box('101번 / 0초 → 00:01:00')+arrow+box('원본 위치는 다시0초'),
        box('한 센서: 180개')+arrow+box('같은 시각에 세 센서')+arrow+box('전체: 540개 관측'),
        box('재생 시작을 1시간 이동')+arrow+box('시각만 1시간 뒤로')+arrow+box('원본 위치와 값은 동일'),
        box('설명용 실행 A')+arrow+box('설명용 실행 B')+arrow+box('같은 원본이어도 다른 실행'),
        box('asset_id: 설비')+arrow+box('origin_cycle_id: 원본')+arrow+box('run_id: 실행'),
        box('설비를 고르기')+arrow+box('실행을 고르기')+arrow+box('센서와 시간 구간 확인'),
        box('개수만 확인하면 부족')+arrow+box('시간 연결 확인')+arrow+box('원본 위치와 실행 확인'),
        box('시각 · 실행 · 출처')+arrow+box('원하는 결과인지 대조')+arrow+box('다음: 관측의 품질 정보'),
    ]
    for index in (2, 5, 7, 8, 10):
        figures[index] = figures[index].replace(arrow, '<div style="height:24px"></div>')
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.layout{grid-template-columns:530px 1fr;gap:42px}.figure{padding:25px}.body{font-size:27px;line-height:1.5}table{font-size:25px}td,th{padding:11px 13px}.figure:after{content:"설명용 재생 흐름"}'
    css += '.body{word-break:keep-all}#s03 table,#s04 table,#s05 table,#s08 table,#s11 table{font-size:23px}'
    pages = []
    for i, ((heading, body), fig) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">재생 시각과 실행</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{fig}</aside><article class="body">{body_html(body)}</article></div><footer><span>재생 시각과 원본 위치, 실행을 함께 구분하기</span><span>{i:02} / 12</span></footer></section>')
    target = folder / '재생시각과실행_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>재생 시각과 실행</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
    records = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width':1640, 'height':940})
        page.goto(target.as_uri())
        page.evaluate('document.fonts.ready')
        for i, (_, body) in enumerate(scenes, 1):
            slide = page.locator(f'#s{i:02}')
            check = slide.evaluate('''s=>{const r=s.getBoundingClientRect();let bad=[];for(const e of s.querySelectorAll('article,article p,table,pre,h1,.figure,.box')){let b=e.getBoundingClientRect();if(b.right>r.right-40||b.bottom>r.bottom-65||b.left<r.left)bad.push(e.textContent.slice(0,40));}return {overflow:bad,text:s.querySelector('article').innerText}}''')
            slide.screenshot(path=str(output/f'S{i:02}.png'))
            assert not check['overflow'], (i, check)
            assert normalize(check['text']) == plain_md(body), (i, 'MD content mismatch')
            records.append({'scene':i, 'overflow':[], 'body_matches_md':True, 'body_text':check['text']})
        browser.close()
    assert normalize(records[5]['body_text']) != plain_md(scenes[5][1].replace('540', '541'))
    (output/'렌더검사.json').write_text(json.dumps({'scenes':records, 'changed_value_rejected':True, 'scope':'HTML 레이아웃·본문대조. 실제20분·PPTX·학생이해 미검증.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

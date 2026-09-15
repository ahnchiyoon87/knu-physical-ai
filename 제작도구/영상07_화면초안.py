"""영상07 전체 본문과 관측 레코드 개념도를 렌더한다. 실제 제품 UI가 아니다."""
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
    folder = ROOT / '이론자료/1회차/영상07'
    source = folder / '관측레코드와출처_덱.md'
    parts = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    box = lambda s: '<div class="box">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        '<div class="number" style="font-size:62px">170.1621</div>'+box('누구의 값? · 어떤 단위?')+box('어느 구간에서 왔을까?'),
        '<div class="tag">관측 하나의 레코드</div>'+box('설비와 센서')+box('값과 단위')+box('원본 위치와 집계'),
        box('수업에서 지정한 설비<br><b>HYD-01</b>')+arrow+box('센서<br><b>PS1 · 압력</b>'),
        box('원본100개')+arrow+box('1초 평균170.1621')+arrow+box('raw_value · unit=bar'),
        box('origin_cycle_id=100')+arrow+box('elapsed_s=0')+arrow+box('PS1 원본 인덱스0~99'),
        '<div class="tag">레코드 안의 agg</div>'+box('min · max')+box('n · source_hz')+'<div class="tag">집계 정보의 작은 묶음</div>',
        box('TS1 raw_value=53.219')+box('TS1 agg=None')+'<div class="tag">값은 있고<br>집계 묶음은 따로 없음</div>',
        box('UCI 파일에서 읽기')+arrow+box('1초로 요약하기')+arrow+box('is_synthetic=False'),
        box('키: sensor_id')+arrow+box('값: PS1')+'<div class="tag">이름으로 정보를 찾기</div>',
        box('TS1 관측60개')+box('PS1 관측60개')+box('FS1 관측60개')+'<div class="tag">한 사이클의 관측180개</div>',
        box('원본 · 사이클 · 설비 · 시각')+arrow+box('map_cycle')+arrow+box('관측 목록180개'),
        box('원본 사이클과 구간')+box('이번 재생에 붙인 시각')+'<div class="tag">다음: 시각과 실행을 구분하기</div>',
    ]
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.layout{grid-template-columns:530px 1fr;gap:42px}.figure{padding:25px}.body{font-size:27px;line-height:1.5}table{font-size:25px}td,th{padding:11px 13px}.figure:after{content:"설명용 관측 구조"}'
    css += '.body{word-break:keep-all}#s03 table,#s05 table{font-size:23px}'
    pages = []
    for i, ((heading, body), fig) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">관측 레코드와 출처</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{fig}</aside><article class="body">{body_html(body)}</article></div><footer><span>숫자와 그 숫자의 설명을 함께 전달하기</span><span>{i:02} / 12</span></footer></section>')
    target = folder / '관측레코드와출처_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>관측 레코드와 출처</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
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
    assert normalize(records[3]['body_text']) != plain_md(scenes[3][1].replace('170.1621', '147.21'))
    (output/'렌더검사.json').write_text(json.dumps({'scenes':records, 'changed_value_rejected':True, 'scope':'HTML 레이아웃·본문대조. 실제20분·PPTX·학생이해 미검증.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

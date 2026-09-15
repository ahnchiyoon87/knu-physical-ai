"""영상11 전체 본문과 조회 조건 개념도를 렌더한다. 실제 제품 UI가 아니다."""
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
    folder = ROOT / '이론자료/1회차/영상11'
    source = folder / '실행과구간조회_덱.md'
    parts = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    box = lambda s: '<div class="box">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        box('설비와 실행')+'<div style="height:24px"></div>'+box('센서와 시간 구간')+'<div style="height:24px"></div>'+box('요청한 관측 선택'),
        box('SELECT · 읽을 항목')+'<div style="height:24px"></div>'+box('FROM · 테이블')+'<div style="height:24px"></div>'+box('WHERE · 조건'),
        box('설비 조건')+'<div style="height:24px"></div>'+box('AND 실행 조건')+'<div style="height:24px"></div>'+box('AND 센서 조건'),
        box('조회 문장의 %s')+'<div style="height:24px"></div>'+box('별도로 전달할 값')+'<div style="height:24px"></div>'+box('문장과 인수 대조'),
        box('시각순')+'<div style="height:24px"></div>'+box('같은 시각의 센서 이름순')+'<div style="height:24px"></div>'+box('ORDER BY'),
        box('선택한 설비·실행')+'<div style="height:24px"></div>'+box('마지막 관측 max(ts)')+'<div style="height:24px"></div>'+box('또는 지정한 until'),
        box('00:02:00~00:02:59')+'<div style="height:24px"></div>'+box('전체 센서 180행')+'<div style="height:24px"></div>'+box('PS1만 60행'),
        box('사이클100 · 센서별29행')+'<div style="height:24px"></div>'+box('사이클101 · 센서별31행')+'<div style="height:24px"></div>'+box('같은60초 · 두사이클'),
        box('00:00:30 제외')+'<div style="height:24px"></div>'+box('00:01:30 포함')+'<div style="height:24px"></div>'+box('시작도 포함하면 +3행'),
        box('내 실행 · 00시 구간')+'<div style="height:24px"></div>'+box('조건 없음 · 01시 구간')+'<div style="height:24px"></div>'+box('개수가 같아도 다른 실행'),
        box('조건에 맞는 관측 없음')+'<div style="height:24px"></div>'+box('빈 결과 0행')+'<div style="height:24px"></div>'+box('측정값0과 구분'),
        box('조회 조건')+'<div style="height:24px"></div>'+box('실제 실행·시간·출처')+'<div style="height:24px"></div>'+box('다음: 작업 확인 기준'),
    ]
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.layout{grid-template-columns:530px 1fr;gap:42px}.figure{padding:25px}.body{font-size:27px;line-height:1.5}table{font-size:25px}td,th{padding:11px 13px}.figure:after{content:"설명용 조회 구조"}'
    css += '.body{word-break:keep-all}#s06 table{font-size:23px}#s06 td,#s06 th{padding:7px 13px}'
    pages = []
    for i, ((heading, body), fig) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">실행과 구간 조회</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{fig}</aside><article class="body">{body_html(body)}</article></div><footer><span>선택 조건과 실제 관측의 실행·시간·출처 대조</span><span>{i:02} / 12</span></footer></section>')
    target = folder / '실행과구간조회_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>실행과 구간 조회</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
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
    assert normalize(records[8]['body_text']) != plain_md(scenes[8][1].replace('183', '184'))
    (output/'렌더검사.json').write_text(json.dumps({'scenes':records, 'changed_value_rejected':True, 'scope':'HTML 레이아웃·본문대조. 실제20분·PPTX·학생이해 미검증.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

"""영상09 전체 본문과 품질 결과 개념도를 렌더한다. 실제 제품 UI가 아니다."""
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
    folder = ROOT / '이론자료/1회차/영상09'
    source = folder / '품질정보읽기_덱.md'
    parts = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    box = lambda s: '<div class="box">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        box('관측을 받음')+'<div style="height:24px"></div>'+box('품질 상태 확인')+'<div style="height:24px"></div>'+box('사용 여부를 남김'),
        box('raw_value · 검사 입력')+'<div style="height:24px"></div>'+box('quality_flag · 상태')+'<div style="height:24px"></div>'+box('value · 사용값'),
        box('설명용 TS1 입력')+'<div style="height:24px"></div>'+box('53.0 → 53.2')+'<div style="height:24px"></div>'+box('OK · value=53.2'),
        box('설명용 TS1 입력')+'<div style="height:24px"></div>'+box('53.0 → 80.0')+'<div style="height:24px"></div>'+box('SPIKE · value=None'),
        box('입력 없음: None')+'<div style="height:24px"></div>'+box('입력 있음: 80.0')+'<div style="height:24px"></div>'+box('사용값은 둘 다 None'),
        box('누락: MISSING · GAP')+'<div style="height:24px"></div>'+box('변화·반복: SPIKE · STUCK')+'<div style="height:24px"></div>'+box('설정 범위: OUT_OF_RANGE'),
        box('첫53.0: OK')+'<div style="height:24px"></div>'+box('여덟 번째53.0: STUCK')+'<div style="height:24px"></div>'+box('현재 값 + 이전 이력'),
        box('시각 순서로 검사')+'<div style="height:24px"></div>'+box('설비·센서별 상태')+'<div style="height:24px"></div>'+box('검사 시작 상태 확인'),
        box('원래 관측의 필드 유지')+'<div style="height:24px"></div>'+box('품질 상태와 사용값 추가')+'<div style="height:24px"></div>'+box('보류된 행도 남김'),
        box('실제 UCI 세 사이클')+'<div style="height:24px"></div>'+box('품질OK: 540개')+'<div style="height:24px"></div>'+box('설비 정상 판정과 구분'),
        box('센서별 플래그 분포')+'<div style="height:24px"></div>'+box('입력값과 사용값 비교')+'<div style="height:24px"></div>'+box('보류된 관측 출처 확인'),
        box('품질 표시가 붙은 관측')+'<div style="height:24px"></div>'+box('PostgreSQL에 저장')+'<div style="height:24px"></div>'+box('다시 읽어 확인'),
    ]
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.layout{grid-template-columns:530px 1fr;gap:42px}.figure{padding:25px}.body{font-size:27px;line-height:1.5}table{font-size:25px}td,th{padding:11px 13px}.figure:after{content:"설명용 품질 구조"}'
    css += '.body{word-break:keep-all}#s06 table{font-size:23px}#s06 td,#s06 th{padding:7px 13px}'
    pages = []
    for i, ((heading, body), fig) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">품질 정보 읽기</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{fig}</aside><article class="body">{body_html(body)}</article></div><footer><span>입력값과 품질 상태, 사용값을 함께 읽기</span><span>{i:02} / 12</span></footer></section>')
    target = folder / '품질정보읽기_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>품질 정보 읽기</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
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
    assert normalize(records[9]['body_text']) != plain_md(scenes[9][1].replace('540', '541'))
    (output/'렌더검사.json').write_text(json.dumps({'scenes':records, 'changed_value_rejected':True, 'scope':'HTML 레이아웃·본문대조. 실제20분·PPTX·학생이해 미검증.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

"""영상10 전체 본문과 저장 경로 개념도를 렌더한다. 실제 제품 UI가 아니다."""
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
    folder = ROOT / '이론자료/1회차/영상10'
    source = folder / '저장과재조회_덱.md'
    parts = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    box = lambda s: '<div class="box">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        box('프로그램 안의 관측')+'<div style="height:24px"></div>'+box('PostgreSQL에 저장')+'<div style="height:24px"></div>'+box('다른 접속에서 읽기'),
        box('CSV · 파일 전달')+'<div style="height:24px"></div>'+box('DB · 기록과 조건 조회')+'<div style="height:24px"></div>'+box('요청한 결과를 확인'),
        box('접속 주소와 포트')+'<div style="height:24px"></div>'+box('사용할 DB 이름')+'<div style="height:24px"></div>'+box('저장·조회 대상 일치'),
        box('observation 테이블')+'<div style="height:24px"></div>'+box('열마다 정보 종류')+'<div style="height:24px"></div>'+box('스키마 · 저장 구조'),
        box('run · 실행 정보')+'<div style="height:24px"></div>'+box('run_id로 연결')+'<div style="height:24px"></div>'+box('observation · 관측'),
        box('id · DB 행')+'<div style="height:24px"></div>'+box('run_id · 실행')+'<div style="height:24px"></div>'+box('origin_cycle_id · 원본'),
        box('프로그램: None')+'<div style="height:24px"></div>'+box('DB: NULL')+'<div style="height:24px"></div>'+box('다른 필드는 보존'),
        box('실행 등록')+'<div style="height:24px"></div>'+box('품질 관측 전달')+'<div style="height:24px"></div>'+box('COPY로 여러 행 저장'),
        box('실행이 없음 → 거부')+'<div style="height:24px"></div>'+box('필수 단위 없음 → 거부')+'<div style="height:24px"></div>'+box('위반한 조건을 확인'),
        box('저장 함수: 540')+'<div style="height:24px"></div>'+box('새 접속: 540')+'<div style="height:24px"></div>'+box('전체 행의 필드 대조'),
        box('앞 사이클 적재')+'<div style="height:24px"></div>'+box('뒤 적재에서 오류')+'<div style="height:24px"></div>'+box('남아 있는 범위 조회'),
        box('저장 전후 비교')+'<div style="height:24px"></div>'+box('필요한 관측 고르기')+'<div style="height:24px"></div>'+box('다음: 실행·시간 조건'),
    ]
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.layout{grid-template-columns:530px 1fr;gap:42px}.figure{padding:25px}.body{font-size:27px;line-height:1.5}table{font-size:25px}td,th{padding:11px 13px}.figure:after{content:"설명용 저장 구조"}'
    css += '.body{word-break:keep-all}#s06 table{font-size:23px}#s06 td,#s06 th{padding:7px 13px}'
    pages = []
    for i, ((heading, body), fig) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">저장과 재조회</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{fig}</aside><article class="body">{body_html(body)}</article></div><footer><span>관측을 저장하고 별도 접속에서 다시 확인하기</span><span>{i:02} / 12</span></footer></section>')
    target = folder / '저장과재조회_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>저장과 재조회</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
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

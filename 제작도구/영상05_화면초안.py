"""영상05 전체 본문과 구간 묶기 개념도를 렌더한다. 실제 제품 UI가 아니다."""
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
    folder = ROOT / '이론자료/1회차/영상05'
    source = folder / '원본을1초구간으로_덱.md'
    parts = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    box = lambda s: '<div class="box">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        box('같은 첫1초')+arrow+box('TS1 1개 · FS1 10개')+box('PS1 100개'),
        box('원본 파일의 한 줄')+arrow+box('순서가 있는 샘플 배열')+arrow+box('인덱스0 → 1 → … → 5,999'),
        box('첫 구간: 0~99')+arrow+box('다음 구간: 100~199')+arrow+box('다음 구간: 200~299'),
        box('묶음0: 0~99')+box('묶음1: 100~199')+'<div class="tag">중간57묶음 생략</div>'+box('묶음59: 5,900~5,999')+'<div class="tag">원본 값이 아닌 위치 번호</div>',
        box('입력: 6,000개')+arrow+box('reshape(60, 100)')+arrow+box('60행 · 각100개'),
        box('원본 파일: 여러 사이클')+arrow+box('사이클100 하나를 선택')+arrow+box('그 안의60개 시간 구간'),
        box('(60, 100)<br>60묶음 × 각100개')+arrow+box('PS1의1초 묶음')+'<div class="tag">(100, 60)은 각0.6초</div>',
        box('TS1: 60 × 1')+box('FS1: 60 × 10')+box('PS1: 60 × 100')+'<div class="tag">공통60묶음 · 각 센서의Hz</div>',
        box('현재 묶음: 샘플100개')+arrow+box('이 묶음에서 계산')+arrow+box('다음 묶음으로 이동'),
        box('시작본도60묶음')+arrow+box('각 묶음의 첫 값만 선택')+arrow+box('결과60개 ≠ 전체 샘플 사용'),
        box('묶음의 모양 확인')+arrow+box('처음·다음·마지막 경계 확인')+arrow+box('다시 펼쳐 전체 입력과 비교'),
        box('원본을 구간별로 모으기')+arrow+box('각 구간의 여러 값')+arrow+box('다음: 첫 값·평균·범위'),
    ]
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.layout{grid-template-columns:530px 1fr;gap:42px}.figure{padding:25px}.body{font-size:27px;line-height:1.5}table{font-size:25px}td,th{padding:11px 13px}.figure:after{content:"설명용 구간 묶기 개념도"}'
    pages = []
    for i, ((heading, body), fig) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">원본을1초 구간으로 묶기</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{fig}</aside><article class="body">{body_html(body)}</article></div><footer><span>긴 원본을 같은 시간의 묶음으로 나누기</span><span>{i:02} / 12</span></footer></section>')
    target = folder / '원본을1초구간으로_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>원본을1초 구간으로 묶기</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
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
    assert normalize(records[3]['body_text']) != plain_md(scenes[3][1].replace('5,900', '5,901'))
    (output/'렌더검사.json').write_text(json.dumps({'scenes':records, 'changed_boundary_rejected':True, 'scope':'HTML 레이아웃·본문대조. 실제20분·PPTX·학생이해 미검증.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

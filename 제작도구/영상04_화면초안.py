"""영상04 전체 본문과 상대 시간 개념도를 렌더한다. 실제 제품 UI가 아니다."""
import argparse
from html import escape
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from 영상02_화면초안 import body_html

ROOT = Path(__file__).resolve().parents[1]


def axis(rows, endpoint, caption):
    """Rows: sensor label, list of relative seconds, right-hand explanation."""
    parts = ['<svg viewBox="0 0 460 340" role="img" aria-label="'+escape(caption)+'">']
    for k, (label, times, note) in enumerate(rows):
        y = 62 + k * 95
        parts.append(f'<text x="10" y="{y-24}" font-size="23">{escape(label)} · {escape(note)}</text>')
        parts.append(f'<line x1="20" y1="{y}" x2="425" y2="{y}" stroke="#96abc8" stroke-width="3"/>')
        for t in times:
            parts.append(f'<circle cx="{20+405*t/endpoint}" cy="{y}" r="6" fill="#225db9"/>')
        parts.append(f'<text x="14" y="{y+30}" font-size="20">0</text><text x="390" y="{y+30}" font-size="20">{endpoint}초</text>')
    parts.append('</svg>')
    return '<div class="tag">'+escape(caption)+'</div>'+''.join(parts)


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
    folder = ROOT / '이론자료/1회차/영상04'
    source = folder / '측정주기와시간축_덱.md'
    parts = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    box = lambda s: '<div class="box">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        box('같은 60초')+arrow+box('60개 · 600개 · 6,000개')+arrow+box('기록하는 빈도가 다름'),
        box('계속 변하는 온도')+arrow+box('정해진 때에 한 번 읽기')+arrow+box('샘플 하나'),
        axis([('TS1', [0], '1개'), ('FS1', [i/10 for i in range(10)], '10개')], 1, '첫 1초의 샘플 위치'),
        box('1Hz → 1초 간격')+arrow+box('10Hz → 0.1초 간격')+arrow+box('100Hz → 0.01초 간격'),
        box('운전 구간<br><b>60초</b>')+arrow+box('측정 빈도를 곱하기')+arrow+box('원본 샘플 개수와 대조'),
        box('PS1 인덱스100')+arrow+box('100 ÷ 100Hz')+arrow+box('<b>상대 시간 1초</b>'),
        axis([('TS1', [10], '10초'), ('FS1', [1], '1초'), ('PS1', [.1], '0.1초')], 10, '모두 인덱스10을 선택'),
        axis([('TS1', [10], '인덱스10'), ('FS1', [10], '인덱스100'), ('PS1', [10], '인덱스1,000')], 10, '모두 상대 시간10초를 선택'),
        box('0초에서 시작')+arrow+box('마지막 샘플<br>59 / 59.9 / 59.99초')+arrow+box('60초는 끝 경계'),
        box('10.05초를 찾으면')+arrow+box('TS1 · FS1<br>원본의 해당 위치 없음')+arrow+box('PS1 · 인덱스1,005'),
        box('10초 이상 · 11초 미만')+arrow+box('1개 / 10개 / 100개')+arrow+box('같은 구간의 서로 다른 개수'),
        box('학생: 목적과 시간 기준')+arrow+box('에이전트: 구현과 출력')+arrow+box('학생: 위치·개수·단위 대조'),
    ]
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.layout{grid-template-columns:530px 1fr;gap:42px}.figure{padding:25px}.body{font-size:27px;line-height:1.5}table{font-size:25px}td,th{padding:11px 13px}.figure:after{content:"설명용 상대 시간 개념도"}'
    pages = []
    for i, ((heading, body), fig) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">측정 주기와 시간축</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{fig}</aside><article class="body">{body_html(body)}</article></div><footer><span>같은 시간의 값을 나란히 보기</span><span>{i:02} / 12</span></footer></section>')
    target = folder / '측정주기와시간축_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>측정 주기와 시간축</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
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
    assert plain_md(scenes[7][1]) != plain_md(scenes[7][1].replace('1,000', '100'))
    (output/'렌더검사.json').write_text(json.dumps({'scenes':records, 'changed_index_rejected':True, 'scope':'HTML 레이아웃·본문대조. 실제20분·PPTX·학생이해 미검증.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()

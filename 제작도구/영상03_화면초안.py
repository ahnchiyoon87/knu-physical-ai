"""영상03의 전체 원문 텍스트와 원본 위치 설명을 HTML 장면으로 만든다."""
from html import escape
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from 영상02_화면초안 import body_html

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT/'이론자료/1회차/영상03'
    source = folder/'센서파일과사이클_덱.md'
    data = json.loads((ROOT/'작업기록/첫날제작_20260915/영상03_원본확인/원본확인.json').read_text(encoding='utf-8'))
    rows = {r['cycle_index']: r for r in data['TS1']['selected_rows']}
    assert rows[100]['physical_line'] == 101 and rows[100]['first_values'][0] == 53.219
    box = lambda s, active=False: '<div class="box'+(' active' if active else '')+'">'+s+'</div>'
    arrow = '<div class="arrow">↓</div>'
    figures = [
        '<div class="tag">TS1</div><div class="value">53.219<small>°C</small></div>'+box('원본의 어디일까?'),
        box('TS1 · 온도')+arrow+box('SENSOR_SPEC')+arrow+box('TS1.txt', True),
        box('60초 운전')+arrow+box('60초 운전')+arrow+box('운전 한 번 = 한 사이클', True),
        '<div class="tag">원본 일부 재구성</div>'+box('사이클0<br>35.570 → 35.492 → …')+'<div class="tag">⋮ 중간 행 생략</div>'+box('사이클100<br>53.219 → 53.207 → …', True),
        box('같은 행 안<br><b>탭으로 나눈 샘플</b>')+arrow+box('실제 줄바꿈<br><b>다음 사이클</b>', True),
        '<div class="tag">머리글 없는 원본</div>'+box('첫 줄부터 센서값', True)+arrow+box('첫 사이클도<br>데이터에 포함'),
        box('파일 줄 번호<br><b>101번째</b>')+arrow+box('코드의 위치 번호<br><b>100</b>', True),
        '<div class="tag">TS1 원본 일부</div>'+''.join(box(f'사이클 {i} · 줄 {rows[i]["physical_line"]}<br><b>{rows[i]["first_values"][0]:.3f}°C</b>', i==100) for i in (99,100,101)),
        box('한 줄의 글자')+arrow+box('탭으로 나누기')+arrow+box('숫자로 해석', True),
        box('TS1 · 사이클100')+arrow+box('원본101번째 줄')+arrow+box('60개 샘플<br>첫 값53.219', True),
        '<div class="tag">같은60초</div>'+''.join(box(f'{s}<br><b>{data[s]["columns_per_row"]:,}개 샘플</b>') for s in ('TS1','FS1','PS1')),
        box('파일의 어디인가?')+arrow+box('원본 위치 확인', True)+arrow+box('어느 시각인가?'),
    ]
    sections = re.split(r'^## (S\d+ .+)$', source.read_text(encoding='utf-8'), flags=re.M)
    scenes = list(zip(sections[1::2], sections[2::2]))
    assert len(scenes) == len(figures) == 12
    previous = (ROOT/'이론자료/1회차/영상02/센서값과단위_화면초안.html').read_text(encoding='utf-8')
    css = re.search(r'<style>(.*?)</style>', previous, re.S).group(1)
    css += '.value{font-size:72px;font-weight:800;color:#225db9;line-height:1.4}.value small{font-size:34px}.box b{font-size:30px}.figure:after{content:"설명용 도형 · 실측 UI 아님"}'
    pages = []
    for i, ((heading, body), figure) in enumerate(zip(scenes, figures), 1):
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">센서 파일과 사이클</div><h1>{escape(heading.split(" ",1)[1])}</h1><div class="layout"><aside class="figure">{figure}</aside><article class="body">{body_html(body)}</article></div><footer><span>표시된 숫자를 원본에서 다시 찾기</span><span>{i:02} / 12</span></footer></section>')
    target = folder/'센서파일과사이클_화면초안.html'
    target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>센서 파일과 사이클</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
    output = ROOT/'작업기록/첫날제작_20260915/영상03_화면검토_v2'
    output.mkdir(parents=True, exist_ok=False)
    records = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1640, 'height': 940})
        page.goto(target.as_uri())
        page.evaluate('document.fonts.ready')
        for i in range(1, 13):
            slide = page.locator(f'#s{i:02}')
            result = slide.evaluate('''s=>{const r=s.getBoundingClientRect();let bad=[];for(const e of s.querySelectorAll('h1,article,article table,article pre,.figure,.box')){const b=e.getBoundingClientRect();if(b.right>r.right-40||b.bottom>r.bottom-65||b.left<r.left)bad.push(e.textContent.slice(0,40));}return {overflow:bad,body_text:s.querySelector('article').innerText}}''')
            assert not result['overflow'], (i,result)
            slide.screenshot(path=str(output/f'S{i:02}.png'))
            records.append({'scene':i,**result})
        browser.close()
    (output/'렌더검사.json').write_text(json.dumps({'scope':'HTML 텍스트와 레이아웃. PPTX/녹화 아님.','scenes':records}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('전12장면 HTML 렌더:',output)


if __name__ == '__main__':
    main()

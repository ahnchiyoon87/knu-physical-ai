"""영상02 Markdown 장면을 설명용 도형과 함께 HTML로 렌더한다."""
from html import escape
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'이론자료/1회차/영상02/센서값과단위_덱.md'
TARGET = SOURCE.with_name('센서값과단위_화면초안.html')


def inline(text):
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'`(.+?)`', r'<code>\1</code>', text)


def body_html(text):
    out = []
    for block in re.split(r'\n\s*\n', text.strip()):
        if block.startswith('```'):
            lines = block.splitlines()
            out.append('<pre>'+escape('\n'.join(lines[1:-1]))+'</pre>')
        elif block.startswith('|'):
            rows = [line.strip().strip('|').split('|') for line in block.splitlines()]
            out.append('<table><thead><tr>'+''.join('<th>'+inline(c.strip())+'</th>' for c in rows[0])+'</tr></thead><tbody>')
            for row in rows[2:]:
                out.append('<tr>'+''.join('<td>'+inline(c.strip())+'</td>' for c in row)+'</tr>')
            out.append('</tbody></table>')
        else:
            out.append('<p>'+inline(block).replace('\n', '<br>')+'</p>')
    return ''.join(out)


FIGURES = [
    '<div class="number">45</div><div class="tag">무엇의 값일까?</div>',
    '<div class="tag">측정 대상</div><div class="number">45</div><div class="label">온도</div>',
    '<div class="label">온도</div><div class="number">45<small>°C</small></div><div class="tag">숫자 + 단위</div>',
    '<div class="box">원본 값 · 단위</div><div class="arrow">↓</div><div class="box active">변환 계산</div><div class="arrow">↓</div><div class="box">변환된 값 · 단위</div>',
    '<div class="box">HYD-01<br><b>TS1 · 온도</b></div><div class="space"></div><div class="box">HYD-02<br><b>TS1 · 온도</b></div>',
    '<div class="box">사람이 알아보는 이름<br><b>유압설비 1호기</b></div><div class="arrow">↕</div><div class="box active">기록을 연결하는 ID<br><b>HYD-01</b></div>',
    '<div class="label">PS1의 안내표</div><div class="box">어느 파일?<br><b>PS1.txt</b></div><div class="box">어떤 단위?<br><b>bar</b></div><div class="box">얼마나 자주?<br><b>1초에100번</b></div>',
    '<div class="box">원본</div><div class="arrow">↓</div><div class="box">설정 → 관측</div><div class="arrow">↓</div><div class="box active">화면에서 대조</div>',
    '<div class="box">학생의 목적 · 조건</div><div class="arrow">↓</div><div class="box">에이전트 구현</div><div class="arrow">↓</div><div class="box active">학생의 결과 판단</div>',
    '<div class="label">내가 이 화면을<br>사용한다면</div><div class="number">?</div><div class="box active">어떤 확인을 요청할까?</div>',
    '<div class="box">정보가 빠졌나?</div><div class="arrow">↓</div><div class="box">서로 잘못 연결됐나?</div><div class="arrow">↓</div><div class="box active">다음에 무엇이 필요한가?</div>',
    '<div class="tag">HYD-01 · TS1</div><div class="number">45<small>°C</small></div><div class="box active">언제? · 원본 어디?</div>',
]
# 모든 그림은 개념 설명이며 제품 UI나 실측 화면이 아니다.


def main():
    text = SOURCE.read_text(encoding='utf-8')
    parts = re.split(r'^## (S\d+ .+)$', text, flags=re.M)
    scenes = list(zip(parts[1::2], parts[2::2]))
    assert len(scenes) == len(FIGURES) == 12
    css = '''
*{box-sizing:border-box}body{margin:0;background:#dce4ed;color:#152b43;font-family:"Malgun Gothic",sans-serif}
section.s{width:1600px;height:900px;background:#fff;position:relative;padding:58px 70px;margin:20px auto;page-break-after:always;overflow:hidden}
.top{color:#3564bd;font-size:22px;font-weight:700;letter-spacing:1px}h1{font-size:46px;margin:16px 0 32px;line-height:1.35}
.layout{display:grid;grid-template-columns:370px 1fr;gap:54px;height:610px;align-items:center}
.figure{border-radius:24px;background:#edf4ff;padding:30px;text-align:center;align-self:stretch;display:flex;flex-direction:column;justify-content:center;border:1px solid #ccdff6;position:relative}
.figure:after{content:"설명용 개념도";position:absolute;bottom:17px;left:0;width:100%;font-size:16px;color:#667b94}
.number{font-size:112px;font-weight:800;line-height:1.3;color:#225db9}.number small{font-size:48px}.label{font-size:35px;font-weight:700;margin:10px}.tag{font-size:26px;color:#3761a3;margin:12px}.box{font-size:25px;line-height:1.6;background:#fff;padding:18px 10px;border:1px solid #ccdbed;border-radius:13px;margin:6px 0}.active{background:#255bb5;color:white;border-color:#255bb5}.arrow{font-size:38px;color:#5480bb;line-height:1.15}.space{height:30px}
.body{font-size:28px;line-height:1.65;min-width:0}p{margin:14px 0}strong{color:#2059b1}table{border-collapse:collapse;width:100%;font-size:27px;margin:20px 0}th{background:#edf3fb;color:#214e8f;text-align:left}td,th{padding:14px 18px;border-bottom:1px solid #dae3ee;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5fa;padding:22px;border-radius:12px;font-size:25px;line-height:1.7;font-family:Consolas,"Malgun Gothic",monospace}code{font-family:Consolas,"Malgun Gothic",monospace;color:#2059b1}
footer{position:absolute;bottom:24px;left:70px;right:70px;border-top:1px solid #e0e7ef;padding-top:13px;color:#738398;font-size:18px;display:flex;justify-content:space-between}
@media print{body{background:#fff}section.s{margin:0}@page{size:1600px 900px;margin:0}}
'''
    pages = []
    for i, ((heading, body), figure) in enumerate(zip(scenes, FIGURES), 1):
        title = heading.split(' ', 1)[1]
        pages.append(f'<section class="s" id="s{i:02}"><div class="top">센서값과 단위</div><h1>{escape(title)}</h1><div class="layout"><aside class="figure">{figure}</aside><article class="body">{body_html(body)}</article></div><footer><span>숫자 하나를 관측으로 읽기</span><span>{i:02} / {len(scenes)}</span></footer></section>')
    TARGET.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>센서값과 단위</title><style>'+css+'</style><body>'+''.join(pages)+'</body></html>', encoding='utf-8')
    output = ROOT/'작업기록/첫날제작_20260915/영상02_화면검토_v3'
    output.mkdir(parents=True, exist_ok=False)
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1640, 'height': 940}, device_scale_factor=1)
        page.goto(TARGET.as_uri())
        page.evaluate('document.fonts.ready')
        checks = []
        for i in range(1, len(scenes)+1):
            slide = page.locator(f'#s{i:02}')
            data = slide.evaluate('''s=>{const r=s.getBoundingClientRect();let bad=[];for(const e of s.querySelectorAll('article,article p,article table,article pre,h1,.figure')){const b=e.getBoundingClientRect();if(b.right>r.right-40||b.bottom>r.bottom-65||b.left<r.left)bad.push(e.tagName+':'+e.textContent.slice(0,50));}return {overflow:bad,text:s.querySelector('article').innerText}}''')
            assert not data['overflow'], (i, data['overflow'])
            slide.screenshot(path=str(output/f'S{i:02}.png'))
            checks.append({'scene': i, 'overflow': data['overflow'], 'body_text': data['text']})
        browser.close()
    (output/'렌더검사.json').write_text(json.dumps({'scope':'HTML 레이아웃 검사. PPTX 렌더/녹화시간 아님.', 'scenes': checks}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'HTML 전{len(scenes)}장면 렌더:', output)


if __name__ == '__main__':
    main()

"""로컬 관제의 실제 브라우저 화면과 요청 내역을 새 폴더에 보관한다."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('output', type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
requests, errors, blocked = [], [], []
with sync_playwright() as engine:
    browser = engine.chromium.launch(headless=True)
    try:
        page = browser.new_page(viewport={'width': 1536, 'height': 864}, device_scale_factor=1)
        def route_request(route):
            request = route.request
            allowed = (request.method in ('GET', 'HEAD') and
                       urlparse(request.url).netloc == 'localhost:8800')
            requests.append({'method': request.method, 'url': request.url, 'allowed': allowed})
            if allowed:
                route.continue_()
            else:
                blocked.append(request.url)
                route.abort()
        page.route('**/*', route_request)
        page.on('pageerror', lambda error: errors.append(str(error)))
        response = page.goto('http://localhost:8800/', wait_until='networkidle')
        assert response and response.status == 200
        page.get_by_text('HYD-01', exact=False).first.wait_for()
        page.screenshot(path=str(args.output / '관제_첫화면.png'), full_page=True)
        (args.output / '화면본문.txt').write_text(page.locator('body').inner_text(), encoding='utf-8')
        report = {'time_utc': datetime.now(timezone.utc).isoformat(), 'url': page.url,
                  'title': page.title(), 'requests': requests, 'page_errors': errors,
                  'blocked_requests': blocked, 'capture': 'Actual Chromium page, no DOM edits or mock responses'}
        (args.output / '캡처기록.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        assert not errors and not blocked, report
        print(json.dumps({'title': report['title'], 'requests': len(requests), 'page_errors': errors}, ensure_ascii=False))
    finally:
        browser.close()

"""별도 검증 DB에 연결된 localhost:8804 관제에서 실제 시나리오를 실행한다.

기존 수업 서버 8800은 읽기만 한다. 8804는 hydops_s04_review DB여야 한다.
승인·조치·유료 모델 호출 없음. 화면/응답 대체 없음.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import subprocess
import time
from urllib.request import Request, urlopen
from playwright.sync_api import sync_playwright

BASE = 'http://localhost:8804'
OLD_EVENT = 'EVT-20270126-090043-HYD-01-e51b'


def api(path, body=None, base=BASE):
    data = None if body is None else json.dumps(body).encode()
    request = Request(base+path, data=data, headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def wait_sim(seconds):
    def sim_time():
        return datetime.fromisoformat(api('/api/state')['sim']['HYD-01']['t'])
    start = sim_time()
    deadline = time.monotonic()+40
    while (sim_time()-start).total_seconds() < seconds:
        if time.monotonic() > deadline:
            raise TimeoutError('시뮬레이터 시간 진행을 확인하지 못했습니다.')
        time.sleep(.3)


def main(output):
    env = json.loads(subprocess.check_output(['docker', 'inspect', 'knu-s04-dashboard-review', '--format', '{{json .Config.Env}}'], text=True))
    assert 'HYDOPS_PG_DSN=postgresql://hydops:hydops@postgres:5432/hydops_s04_review' in env
    assert 'HYDOPS_AGENT_MODE=offline' in env
    output.mkdir(parents=True, exist_ok=False)
    previous = api('/api/events/'+OLD_EVENT, base='http://localhost:8800')
    cases = []
    errors = []
    requests = []
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1600, 'height': 1100}, device_scale_factor=1.25)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: requests.append({'method': request.method, 'url': request.url}))
        try:
            for name, button, duration, event_type in [
                ('단발급등', 'inject-spike', 7, None),
                ('센서결측', 'inject-dropout', 10, 'SENSOR_FAULT'),
                ('냉각저하', 'inject-cooling', 75, 'COOLING_ANOMALY'),
            ]:
                state = api('/api/control', {'reset': True, 'seed': 42, 'scenario': 's04-'+name, 'speed': 10, 'paused': False})
                wait_sim(30)
                page.goto(BASE+'/', wait_until='networkidle')
                if button == 'inject-spike':
                    page.get_by_role('button', name='단발 급등', exact=True).click()
                else:
                    page.get_by_test_id(button).click()
                wait_sim(duration)
                api('/api/control', {'paused': True})
                selected = None
                deadline = time.monotonic()+25
                while True:
                    events = api('/api/events')
                    matches = [e for e in events if e['asset_id'] == 'HYD-01' and e['event_type'] == event_type]
                    if not event_type:
                        assert not events, events
                        break
                    if matches:
                        assert len(matches) == 1
                        selected = api('/api/events/'+matches[0]['event_id'])
                        if selected['event']['status'] in ('PENDING_APPROVAL', 'SENSOR_CHECK'):
                            break
                    if time.monotonic() > deadline:
                        raise TimeoutError('기대 사건 상태를 확인하지 못했습니다.')
                    time.sleep(.4)
                series = api('/api/series?asset_id=HYD-01&seconds=180')
                flags = [r['flag'] for r in series['series']['TS1']]
                assert ('SPIKE' in flags) if name == '단발급등' else True
                if event_type:
                    assert selected['actions'] == [] and selected['approvals'] == []
                    if event_type == 'SENSOR_FAULT':
                        assert selected['event']['evidence']['flag'] == 'GAP'
                    else:
                        assert selected['event']['evidence']['valid_samples'] == 10
                    page.get_by_test_id('event-'+event_type).click()
                    detail_panel = page.locator('section.detail').filter(has=page.locator('h2'))
                    detail_panel.get_by_text(selected['event']['event_id'], exact=True).wait_for()
                    page.get_by_test_id('status-'+selected['event']['event_id']).filter(has_text=('센서 점검' if event_type == 'SENSOR_FAULT' else '승인 대기')).wait_for()
                    detail_panel.screenshot(path=str(output/(name+'_상세.png')))
                page.screenshot(path=str(output/(name+'_전체.png')), full_page=True)
                (output/(name+'_화면본문.txt')).write_text(page.locator('body').inner_text(), encoding='utf-8')
                case = {'name': name, 'run_id': state['run_id'], 'events': events, 'detail': selected, 'series': series, 'state': api('/api/state')}
                cases.append(case)
                (output/(name+'_결과.json')).write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding='utf-8')
            after = api('/api/events/'+OLD_EVENT, base='http://localhost:8800')
            assert previous == after, '기존 사건 기록이 변경됐습니다.'
            assert not errors, errors
            assert all('/decision' not in r['url'] for r in requests)
            report = {'scope': '격리 PostgreSQL DB의 실제 원본 관제 UI·offline 처리. 학생 완주 또는 유료모델 검증 아님.',
                      'original_event_unchanged': True, 'page_errors': errors, 'requests': requests,
                      'cases': [{'name': c['name'], 'run_id': c['run_id'], 'event_count': len(c['events']),
                                 'status': c['detail']['event']['status'] if c['detail'] else None} for c in cases]}
            (output/'검증결과.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(report['cases'], ensure_ascii=False))
        except Exception as error:
            page.screenshot(path=str(output/'실패시점.png'), full_page=True)
            (output/'실패기록.json').write_text(json.dumps({'error': str(error), 'page_errors': errors, 'requests': requests}, ensure_ascii=False, indent=2), encoding='utf-8')
            raise
        finally:
            api('/api/control', {'paused': True})
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    main(parser.parse_args().output)

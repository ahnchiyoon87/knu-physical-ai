"""Local Vertex extension usage collector. Never sends a model request.

Records extension-estimated cost, NOT Google Cloud billed cost. Use one VS Code
measurement session at a time: extension logs do not identify the workspace.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNTIME = HERE / '.runtime'
DEFAULT_LOGS = Path(os.environ.get('APPDATA', '')) / 'Code/User/globalStorage/jorsm.vertex-ai-models-chat-provider/usage_logs'


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def baseline(logs):
    result = {}
    for p in sorted(logs.glob('*.jsonl')):
        data = p.read_bytes()
        if data and not data.endswith(b'\n'):
            raise ValueError('Usage log is being written; wait for the request to finish.')
        result[p.name] = {'size': len(data), 'sha256': digest(data)}
    return result


def collect(logs, before):
    records = []
    current = {p.name: p for p in logs.glob('*.jsonl')}
    if set(before) - set(current):
        raise ValueError('A baseline log disappeared; cannot establish complete usage.')
    for name, p in sorted(current.items()):
        raw = p.read_bytes()
        old = before.get(name, {'size': 0, 'sha256': digest(b'')})
        if digest(raw[:old['size']]) != old['sha256']:
            raise ValueError('A usage log was truncated or changed: ' + name)
        delta = raw[old['size']:]
        if delta and not delta.endswith(b'\n'):
            raise ValueError('Request log is incomplete; wait and run end again.')
        for line in delta.splitlines():
            obj = json.loads(line)
            tokens = obj.get('tokens', {})
            required = ('input', 'output', 'cache_read', 'cache_create')
            if any(type(tokens.get(k)) not in (int, float) or tokens[k] < 0 for k in required):
                raise ValueError('Missing or invalid token fields; do not treat as zero.')
            cost = obj.get('cost')
            if type(cost) not in (int, float) or cost < 0:
                raise ValueError('Missing cost estimate; cannot mark this record complete.')
            records.append({'timestamp': obj['timestamp'], 'model': obj['model'],
                            **{k: tokens[k] for k in required}, 'estimated_usd': cost})
    return records


def prepare(day):
    if not re.fullmatch(r'P0[1-9]|I0[1-9]|I10', day):
        raise ValueError('Use P01..P09 or I01..I10')
    target = RUNTIME / 'work' / day
    if target.exists():
        return target / 'equipment-assistant'
    prefix = '실' if day[0] == 'P' else '통'
    source = ROOT / '10_실습/공통코드/20260914_185519' / f'{prefix}{int(day[1:]):02d}-start.zip'
    with zipfile.ZipFile(source) as z:
        for item in z.infolist():
            candidate = (target / item.filename).resolve()
            if not candidate.is_relative_to(target.resolve()):
                raise ValueError('Unsafe archive path')
        target.mkdir(parents=True)
        z.extractall(target)
    app = target / 'equipment-assistant'
    if not app.is_dir():
        raise ValueError('Unexpected starter archive layout')
    save(target / 'source.json', {'zip': str(source.relative_to(ROOT)),
                                  'sha256': digest(source.read_bytes()),
                                  'basis': '현재 배포본; HydOps 조정안 반영 전'})
    return app


def begin(args):
    active = RUNTIME / 'active.json'
    if active.exists():
        raise ValueError('An active measurement exists. End it before starting another.')
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]', args.project):
        raise ValueError('Enter the explicit measurement project ID.')
    app = prepare(args.day)
    # Workspace settings only. Global VS Code settings and ADC are not changed.
    settings = app / '.vscode/settings.json'
    existing = json.loads(settings.read_text(encoding='utf-8')) if settings.exists() else {}
    if settings.exists():
        save(RUNTIME / 'settings-backup' / (uuid.uuid4().hex + '.json'), existing)
    existing.update({'vertexAiChat.projectId': args.project,
                     'vertexAiChat.enableUserLabel': True,
                     'vertexAiChat.userLabelValue': 'knu-measure',
                     'vertexAiChat.enableProjectLabel': True,
                     'vertexAiChat.projectLabelValue': 'knu-' + args.day.lower(),
                     'vertexAiChat.hideBillingWarning': False})
    save(settings, existing)
    session = {'session_id': uuid.uuid4().hex, 'day': args.day, 'project': args.project,
               'expected_model': args.model, 'start': now(), 'logs': str(args.logs.resolve()),
               'baseline': baseline(args.logs), 'work': str(app),
               'basis': 'current_distribution_before_hydops_revision'}
    save(active, session)
    print('Measurement boundary started; no API call was made.')
    print('Open this folder in VS Code:', app)
    print('Select the specified model AND utility model. Other Vertex sessions must be idle.')
    print('Model discovery may itself send requests; these belong to this measurement.')


def end(args):
    active = RUNTIME / 'active.json'
    session = json.loads(active.read_text(encoding='utf-8'))
    records = collect(Path(session['logs']), session['baseline'])
    result = {k: v for k, v in session.items() if k not in ('baseline', 'logs', 'project', 'work')}
    result.update({'end': now(), 'status': args.status,
                   'measurement_scope': 'coding_agent_extension_only',
                   'cost_basis': 'local_catalog_estimate_not_cloud_invoice',
                   'records': records, 'models': sorted({r['model'] for r in records}),
                   'calls': len(records), 'billing_verified': False})
    for k in ('input', 'output', 'cache_read', 'cache_create', 'estimated_usd'):
        result[k] = sum(r[k] for r in records) if records else None
    if not records:
        result['status'] = 'no_usage_observed'
    result['model_review_required'] = any(r['model'] != session['expected_model'] for r in records)
    output = RUNTIME / 'sessions' / (session['session_id'] + '.json')
    save(output, result)
    active.rename(RUNTIME / (session['session_id'] + '.boundary.json'))
    export()
    print('Saved session:', output)
    print('Observed calls:', len(records), '| User-declared outcome:', result['status'])
    print('Application APIs and infrastructure are not included. Reconcile with Cloud Billing.')


def export():
    sessions = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((RUNTIME / 'sessions').glob('*.json'))]
    rows = []
    for day in [f'P{i:02}' for i in range(1, 10)] + [f'I{i:02}' for i in range(1, 11)]:
        ds = [s for s in sessions if s['day'] == day]
        observed = [s for s in ds if s['calls']]
        row = {'day': day, 'sessions': len(ds),
               'status': '미측정' if not observed else ('완주(사용자 기록)' if any(s['status'] == 'completed' for s in observed) else '부분 측정'),
               'models': ', '.join(sorted({m for s in ds for m in s['models']}))}
        for k in ('calls', 'input', 'output', 'cache_read', 'cache_create', 'estimated_usd'):
            row[k] = sum(s[k] for s in observed) if observed else None
        rows.append(row)
    save(RUNTIME / 'day_totals.json', rows)
    with (RUNTIME / 'day_totals.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print('Updated .runtime/day_totals.csv and day_totals.json; all retries remain included.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('export')
    prep = sub.add_parser('prepare')
    prep.add_argument('--day', required=True)
    b = sub.add_parser('begin')
    b.add_argument('--day', required=True)
    b.add_argument('--project', required=True)
    b.add_argument('--model', required=True)
    b.add_argument('--logs', type=Path, default=DEFAULT_LOGS)
    e = sub.add_parser('end')
    e.add_argument('--status', choices=('completed', 'partial', 'failed'), required=True)
    args = p.parse_args()
    if args.command == 'begin':
        begin(args)
    elif args.command == 'end':
        end(args)
    elif args.command == 'prepare':
        print(prepare(args.day))
    else:
        export()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print('Not completed:', exc, file=sys.stderr)
        sys.exit(1)

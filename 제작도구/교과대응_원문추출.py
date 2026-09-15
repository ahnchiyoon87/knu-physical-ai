"""원본을 수정하지 않고 실라버스·교재 회차표와 학교 일정 대조 근거를 저장한다."""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'lecture-manufacturing-physical-ai-platform'
OUT = ROOT / '작업기록' / '교과대응_20260915'
OUT.mkdir(parents=True, exist_ok=True)
W = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
S = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

docx = next(SOURCE.glob('*.docx'))
paragraphs = []
with ZipFile(docx) as z:
    body = ET.fromstring(z.read('word/document.xml')).find('w:body', W)
    for i, item in enumerate(body):
        if item.tag.endswith('}tbl'):
            paragraphs.append(f'\nTABLE {i}')
            for j, row in enumerate(item.findall('w:tr', W)):
                cells = [''.join(t.text or '' for t in cell.findall('.//w:t', W)) for cell in row.findall('w:tc', W)]
                paragraphs.append(f'R{j}: ' + ' | '.join(cells))
        else:
            text = ''.join(t.text or '' for t in item.findall('.//w:t', W))
            if text:
                paragraphs.append(f'P{i}: {text}')
    for name in z.namelist():
        if name.startswith('word/media/'):
            (OUT / Path(name).name).write_bytes(z.read(name))
(OUT / '실라버스_원문.txt').write_text('\n'.join(paragraphs), encoding='utf-8')

schedule_path = ROOT / '강의계획과운영/받은자료/학교편성_기존초안.json'
schedule = json.loads(schedule_path.read_text(encoding='utf-8-sig'))
book_rows = []
for p in sorted(SOURCE.glob('textbooks/*/*.md')):
    lines = p.read_text(encoding='utf-8-sig').splitlines()
    if not re.match(r'[PI]\d\d_', p.name):
        continue
    date = re.search(r'\d{4}-\d{2}-\d{2}', lines[2]).group()
    cohort = '실전반' if p.name.startswith('P') else '통합반'
    slot = next(x for x in schedule['offline'] if x['cohort'] == cohort and x['date'] == date)
    row = dict(id=p.name[:3], path=str(p.relative_to(SOURCE)).replace('\\','/'), sha256=sha(p), lines=len(lines),
               title=lines[0].lstrip('# '), date=date, school_id=slot['id'], school_row_id=slot['source_row_id'],
               school_time=slot['time'], hours=slot['hours'], header=lines[:6],
               activities=[f'{i+1}: {v}' for i,v in enumerate(lines) if v.startswith('## ') and '50분' in v])
    book_rows.append(row)

xlsx = ROOT / '강의계획과운영/받은자료/KNU_PhysicalAI_uEngine.xlsx'
with ZipFile(xlsx) as z:
    strings = [''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml'))]
    def sheet(n):
        rows=[]
        for r in ET.fromstring(z.read(f'xl/worksheets/sheet{n}.xml')).findall('.//s:sheetData/s:row', S):
            d={}
            for c in r:
                v=c.find('s:v',S)
                if v is not None:
                    d[re.sub(r'\d','',c.get('r'))]=strings[int(v.text)] if c.get('t')=='s' else v.text
            rows.append(d)
        return rows
    offline=sheet(2)
    videos=sheet(3)
checks=[]
for item in schedule['offline']:
    row=next(r for r in offline if r.get('A')==item['source_row_id'])
    checks.append({'id':item['id'],'matches':row['B']==item['date'] and row['F']==item['time'] and float(row['G'])==item['hours']})
for item in schedule['videos']:
    row=next(r for r in videos if r.get('D')==item['cohort'] and r.get('E')==item['source_video'])
    checks.append({'id':item['id'],'matches':row['B']==item['deadline'] and row['C']==item['publish'] and float(row['H'])==item['hours']})
result={'source_docx':str(docx),'source_sha256':sha(docx),'xlsx_sha256':sha(xlsx),
        'xlsx_matches_recorded_hash':sha(xlsx)==schedule['source_sha256'],
        'books':book_rows,'schedule_checks':checks,
        'scope':'DOCX 본문과 전체 표, 교재 19개의 회차표와 활동 제목. 교재 전체 본문과 코드 감사는 아님.',
        'offline_hours':{c:sum(x['hours'] for x in schedule['offline'] if x['cohort']==c) for c in ['실전반','통합반']},
        'online_hours':{c:sum(x['hours'] for x in schedule['videos'] if x['cohort']==c) for c in ['실전반','통합반']}}
(OUT/'원문과일정_대조.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'books':len(book_rows),'schedule_checks':len(checks),'all_match':all(x['matches'] for x in checks),'xlsx_hash_match':result['xlsx_matches_recorded_hash'],'offline':result['offline_hours'],'online':result['online_hours']},ensure_ascii=False))
if not all(x['matches'] for x in checks) or not result['xlsx_matches_recorded_hash']:
    raise SystemExit(1)

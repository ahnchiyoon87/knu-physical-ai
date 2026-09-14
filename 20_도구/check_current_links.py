"""Check local Markdown link targets in current teaching documents, not archives."""
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[1]
PATTERN=re.compile(r'\]\((<[^>]+>|[^)\n]+)\)')
with tempfile.TemporaryDirectory(prefix='knu-links-') as temp:
    folder=Path(temp);(folder/'ok.md').write_text('ok',encoding='utf-8')
    targets=[m.group(1).strip('<>') for m in PATTERN.finditer('[valid](ok.md) [broken](<missing.md>)')]
    assert targets==['ok.md','missing.md']
    assert [(folder/t).exists() for t in targets]==[True,False]
files=list((ROOT/'00_문서').rglob('*.md'))+list((ROOT/'10_실습/학생가이드').rglob('*.md'))
files+=[ROOT/'10_실습/README.md',ROOT/'10_실습/일차별_배포/README.md']
errors=[];checked=0
for path in files:
    source=re.sub(r'```.*?```','',path.read_text(encoding='utf-8'),flags=re.S)
    for match in PATTERN.finditer(source):
        target=match.group(1).strip().strip('<>')
        if urlsplit(target).scheme or target.startswith('#'):continue
        target=unquote(target.split('#')[0]);checked+=1
        if not (path.parent/target).exists():errors.append({'file':str(path.relative_to(ROOT)), 'target':target})
report={'files':len(files),'local_links':checked,'errors':errors,'valid_and_missing_fixture_checked':True,'scope':'로컬 대상 존재. 온라인 URL과 렌더는 검사하지 않음'}
(ROOT/'30_기록/현재문서_링크검사.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(bool(errors))

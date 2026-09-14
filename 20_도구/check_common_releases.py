"""Fresh extraction and complete package sets; no service/model execution."""
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]


def exact_names(actual,expected):
    if len(actual)!=len(set(actual)) or set(actual)!=set(expected):raise ValueError('압축 경로 집합 불일치')


def main():
    exact_names(['a'],{'a'})
    try:exact_names(['a','b'],{'a'})
    except ValueError:pass
    else:raise AssertionError('추가 파일을 놓쳤습니다')
    packages=json.loads((ROOT/'30_기록/공통배포_매니페스트.json').read_text(encoding='utf-8'))['records']
    code=json.loads((ROOT/'30_기록/공통코드_매니페스트.json').read_text(encoding='utf-8'))['records']
    results=[]
    for record in packages:
        start=next(r for r in code if r['id']==record['starter'])
        path=ROOT/record['archive'];assert hashlib.sha256(path.read_bytes()).hexdigest()==record['archive_hash']
        with zipfile.ZipFile(path) as z:
            exact_names(z.namelist(),record['files'])
            for name,h in record['files'].items():
                assert hashlib.sha256(z.read(name)).hexdigest()==h,name
                parts=Path(name).parts
                assert not Path(name).is_absolute() and '..' not in parts
                assert not any(p in {'.env','.venv','node_modules','.git','__pycache__'} for p in parts)
                assert '온라인대본.md' not in parts
            actual={name.removeprefix('프로젝트/equipment-assistant/'):h for name,h in record['files'].items() if name.startswith('프로젝트/equipment-assistant/')}
            assert actual==start['files']
            with tempfile.TemporaryDirectory(prefix='knu-common-release-') as tmp:
                z.extractall(tmp);base=Path(tmp);links=0;missing=[]
                for name in record['files']:
                    if not name.endswith('.md') or name.startswith('프로젝트/'):continue
                    p=base/name;text=re.sub(r'```.*?```','',p.read_text(encoding='utf-8'),flags=re.S)
                    for raw in re.findall(r'\]\((<[^>]+>|[^)]+)\)',text):
                        target=unquote(raw.strip('<>').split('#',1)[0])
                        if not target or re.match(r'^[a-zA-Z]+:',target):continue
                        links+=1
                        if not (p.parent/target).exists():missing.append({'file':name,'target':target})
                results.append({'id':record['id'],'files':len(record['files']),'student_document_links':links,
                                'missing_links':missing,'starter_code_hashes_match':True})
    report={'results':results,'checker_valid_and_invalid_verified':True,
            'scope':'19 ZIPs exact paths/hash, fresh extraction, student document local links, exact prior-stage code hashes and excluded runtime paths. Existing API import evidence applies to identical code; no live lab/GUI/model checks.'}
    (ROOT/'30_기록/공통배포_검사.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    failures=[r for r in results if r['missing_links']]
    print(json.dumps({'releases':len(results),'failures':failures},ensure_ascii=False))
    raise SystemExit(bool(failures))


if __name__=='__main__':main()

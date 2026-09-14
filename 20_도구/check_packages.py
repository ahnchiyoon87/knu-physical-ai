"""Check exact archive contents and imports from fresh extraction, without DB/model calls."""
import ast
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PYTHON=ROOT/'10_실습/완성본/equipment-assistant/.venv/Scripts/python.exe'


def syntax(folder):
    count=0
    for path in folder.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path));count+=1
    return count


def check(record):
    with zipfile.ZipFile(ROOT/record['archive']) as z:
        expected={'equipment-assistant/'+name for name in record['files']}
        if set(z.namelist())!=expected or len(z.namelist())!=len(expected):raise ValueError('ZIP 구성 불일치')
        for name,digest in record['files'].items():
            if hashlib.sha256(z.read('equipment-assistant/'+name)).hexdigest()!=digest:raise ValueError('ZIP 해시 불일치')
            parts=Path(name).parts
            if Path(name).is_absolute() or '..' in parts:raise ValueError('ZIP 경로 이탈')
            if any(x in parts for x in ['.venv','node_modules','.git','__pycache__']) or Path(name).name=='.env':
                raise ValueError('배포 제외 파일 포함')
        with tempfile.TemporaryDirectory(prefix='knu-package-') as temp:
            z.extractall(temp);folder=Path(temp)/'equipment-assistant';count=syntax(folder)
            if (folder/'backend/api.py').exists():
                script="from backend.api import app; print(len(app.routes))"
                env={**os.environ,'PYTHONUTF8':'1','PYTHONPATH':str(folder),'RAGAS_DO_NOT_TRACK':'true','DEEPEVAL_TELEMETRY_OPT_OUT':'YES'}
                result=subprocess.run([str(PYTHON),'-c',script],cwd=folder,env=env,text=True,capture_output=True,encoding='utf-8',timeout=45)
                if result.returncode:raise ValueError(result.stderr[-3000:])
                routes=int(result.stdout.strip().splitlines()[-1])
            else:routes=0
    return {'id':record['id'],'python_files':count,'api_routes':routes,'archive_files':len(expected),'result':'pass'}


def main():
    # A new checker must reject a damaged input, not merely accept current outputs.
    with tempfile.TemporaryDirectory(prefix='knu-checker-') as temp:
        path=Path(temp)/'broken.py';path.write_text('def broken(:\n',encoding='utf-8')
        try:syntax(Path(temp))
        except SyntaxError:rejected=True
        else:raise AssertionError('깨진 구문을 잡지 못했습니다')
        path.write_text('value=1\n',encoding='utf-8');assert syntax(Path(temp))==1
    records=[]
    for name in ['출발본_매니페스트.json','완성본_매니페스트.json']:
        records+=json.loads((ROOT/'30_기록'/name).read_text(encoding='utf-8'))
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[(item,pool.submit(check,item)) for item in records]
        for item,future in futures:
            try:results.append(future.result())
            except Exception as exc:results.append({'id':item['id'],'result':'failed','error':str(exc)})
    report={'scope':'실제 ZIP 재추출·정확한 파일 집합/해시·구문·API import. DB·모델·학생 실습 완주 미실행',
        'checker_valid_and_invalid_verified':rejected,'results':results}
    (ROOT/'30_기록/패키지_구조검사.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    failures=[item for item in results if item['result']!='pass']
    print(json.dumps({'packages':len(results),'failed':failures},ensure_ascii=False))
    raise SystemExit(bool(failures))


if __name__=='__main__':main()

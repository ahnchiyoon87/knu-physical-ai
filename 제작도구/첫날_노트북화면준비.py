from pathlib import Path
import subprocess
import shutil
import secrets
import json

root = Path(__file__).resolve().parents[1]
work = root / '작업기록/첫날제작_20260915/노트북실제화면_v1'
work.mkdir(exist_ok=False)
shutil.copy2(root / '실습자료/1일차/완성본/integrated/S01_sensor_flow.ipynb', work)
runtime = root / '.runtime'
runtime.mkdir(exist_ok=True)
token = secrets.token_urlsafe(32)
(runtime / 'notebook-review-token').write_text(token,encoding='utf-8')
mounts = ['--mount',f'type=bind,source={root / "플랫폼코드"},target=/course/플랫폼코드,readonly',
          '--mount',f'type=bind,source={work},target=/course/student-work']
command = ['docker','run','--rm',*mounts,'-w','/course/student-work',
           '-e','HYDOPS_AGENT_MODE=offline','knu-hydops-notebook-ui:review',
           'jupyter','nbconvert','--to','notebook','--execute','S01_sensor_flow.ipynb',
           '--output','관측_실행결과.ipynb','--ExecutePreprocessor.timeout=120']
result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
(work/'실행기록.json').write_text(json.dumps({'command':command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},ensure_ascii=False,indent=2),encoding='utf-8')
if result.returncode: raise SystemExit(result.stderr)
subprocess.run(['docker','run','-d','--name','knu-notebook-review',*mounts,
                '--mount',f'type=bind,source={root / "제작도구/노트북UI_호환설정.py"},target=/root/.jupyter/jupyter_server_config.py,readonly',
                '-p','127.0.0.1:8889:8888','-e',f'JUPYTER_TOKEN={token}',
                '-e','HYDOPS_AGENT_MODE=offline','-w','/course/student-work',
                'knu-hydops-notebook-ui:review','jupyter','lab','--ip=0.0.0.0',
                '--port=8888','--no-browser','--allow-root',
                '--ServerApp.root_dir=/course/student-work'],check=True,capture_output=True)
print('Executed notebook saved; authenticated local review server on port 8889. Token not printed.')

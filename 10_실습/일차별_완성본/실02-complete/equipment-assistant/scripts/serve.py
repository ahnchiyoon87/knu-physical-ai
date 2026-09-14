"""Run the local processes together; no models or database migrations are started."""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
processes=[]
commands=[ [sys.executable,'-m','uvicorn','backend.api:app','--host','0.0.0.0','--port',os.getenv('PORT','8000')] ]
if os.getenv('SERVE_FRONTEND_DEV','false').lower()=='true':
    commands.append(['npm.cmd' if os.name=='nt' else 'npm','run','dev','--','--host','127.0.0.1'])
try:
    for command in commands:
        processes.append(subprocess.Popen(command,cwd=ROOT/'frontend' if command[0].startswith('npm') else ROOT))
    while all(process.poll() is None for process in processes):
        time.sleep(.5)
    raise SystemExit('한 서비스가 종료되어 함께 종료합니다. 위 오류를 확인하세요.')
except KeyboardInterrupt:
    pass
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill()

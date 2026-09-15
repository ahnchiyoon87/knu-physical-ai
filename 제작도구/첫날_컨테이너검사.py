"""개인 작업본을 동일한 플랫폼·원본 데이터에 연결해 검사한다.

코딩 에이전트가 실행할 준비 도구. 학생에게 명령 문법 암기를 요구하지 않는다.
"""
from pathlib import Path
import argparse
import json
import subprocess
from datetime import datetime, timezone

PROJECT=Path(__file__).resolve().parents[1]

def run(folder: Path, record: Path, notebook=False):
    folder=folder.resolve()
    if PROJECT not in folder.parents or not (folder/'test_check.py').is_file():
        raise ValueError('프로젝트 안의 test_check.py가 있는 작업 폴더를 지정하세요.')
    if record.exists():
        raise FileExistsError('기존 검증 기록을 보존합니다. 새 기록 이름을 지정하세요.')
    command=['docker','run','--rm','--network','knu-hydops-local_default',
        '-e','HYDOPS_AGENT_MODE=offline',
        '-e','HYDOPS_PG_DSN=postgresql://hydops:hydops@postgres:5432/hydops',
        '-e','HYDOPS_NEO4J_URI=bolt://neo4j:7687',
        '--mount',f'type=bind,source={PROJECT / "플랫폼코드"},target=/course/플랫폼코드,readonly',
        '--mount',f'type=bind,source={folder},target=/course/student-work',
        'knu-hydops-notebook:development' if notebook else 'knu-hydops-local:development',
        'python','-m','pytest','/course/student-work/test_check.py','-q','-p','no:cacheprovider']
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8',errors='replace')
    record.parent.mkdir(parents=True,exist_ok=True)
    record.write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),
        'command':command,'exit_code':result.returncode,'output':result.stdout,
        'scope':'실행 환경에서 제공 테스트만 확인. 학생 완주·비용 측정 아님.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(result.stdout)
    return result.returncode

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    parser.add_argument('record',type=Path)
    parser.add_argument('--notebook',action='store_true')
    args=parser.parse_args()
    raise SystemExit(run(args.folder,args.record,args.notebook))

"""한글 폴더명을 유지하며 Docker에 필요한 파일만 tar 입력으로 전달한다."""
from pathlib import Path
import argparse
import subprocess
import tarfile
import tempfile

PROJECT = Path(__file__).resolve().parents[1]

def build(notebook=False):
    root = PROJECT / ('제작도구' if notebook else '플랫폼코드')
    names = ['Dockerfile.notebook'] if notebook else [
        'Dockerfile', 'requirements.txt', 'hydops', 'labplatform',
        'skills', 'sql', 'scripts', 'tests', 'data/reduced']
    def include(info):
        parts = Path(info.name).parts
        if any(x in parts for x in ('.env', '__pycache__', '.pytest_cache', '.git', '.venv')):
            return None
        if info.name.startswith('labplatform/data/'):
            return None
        return info
    with tempfile.TemporaryFile() as data:
        with tarfile.open(fileobj=data, mode='w:gz') as archive:
            for name in names:
                archive.add(root / name, arcname='Dockerfile' if notebook else name, filter=include)
        data.seek(0)
        tag = 'knu-hydops-notebook:development' if notebook else 'knu-hydops-local:development'
        subprocess.run(['docker', 'build', '-t', tag, '-'], stdin=data, check=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notebook', action='store_true')
    args=parser.parse_args()
    build(args.notebook)

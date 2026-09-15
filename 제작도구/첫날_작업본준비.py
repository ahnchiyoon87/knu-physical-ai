"""원문을 보존하며 첫날 개인 작업본과 플랫폼 import 경로를 준비한다.

실습 정답은 채우지 않는다. Python 패키지 설치/DB 기동/모델 호출은 하지 않는다.
"""
from pathlib import Path
import argparse
import json
import shutil

PROJECT = Path(__file__).resolve().parents[1]


def prepare(cohort: str, destination: Path) -> Path:
    source = PROJECT / '실습자료' / '1일차' / '원문시작본' / cohort
    destination = destination.resolve()
    # 노트북은 이동 가능한 상대 탐색으로 플랫폼코드를 찾는다.
    if PROJECT not in destination.parents:
        raise ValueError('작업본은 강의 프로젝트 안의 새 개인 폴더에 만들어 주세요.')
    if destination.exists():
        raise FileExistsError(f'기존 작업을 보존합니다. 다른 새 폴더를 지정하세요: {destination}')
    if not (PROJECT / '플랫폼코드' / 'hydops').is_dir():
        raise FileNotFoundError('플랫폼코드/hydops가 없습니다.')
    shutil.copytree(source, destination)
    if cohort == 'integrated':
        notebook = destination / 'S01_sensor_flow.ipynb'
        document = json.loads(notebook.read_text(encoding='utf-8'))
        old = "SYSTEM = next(p / 'system' for p in [Path.cwd(), *Path.cwd().parents] if (p / 'system' / 'hydops').exists())"
        new = "SYSTEM = next(p / '플랫폼코드' for p in [Path.cwd(), *Path.cwd().parents] if (p / '플랫폼코드' / 'hydops').exists())"
        changed = 0
        for cell in document['cells']:
            body = ''.join(cell['source'])
            if old in body:
                body = body.replace(old, new)
                changed += 1
            body = body.replace('lecture/system', '플랫폼코드').replace('system/data/raw', '플랫폼코드/data/raw')
            cell['source'] = body.splitlines(keepends=True)
        if changed != 1:
            raise ValueError(f'노트북 준비 셀 구조를 확인하세요: 일치 {changed}개')
        notebook.write_text(json.dumps(document, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    # pytest 실행 위치와 관계없이 같은 프로젝트의 제공 코드를 불러온다.
    (destination / 'conftest.py').write_text(
        'from pathlib import Path\nimport sys\n'
        "platform = next(p / '플랫폼코드' for p in Path(__file__).resolve().parents "
        "if (p / '플랫폼코드' / 'hydops').is_dir())\n"
        'sys.path.insert(0, str(platform))\n', encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cohort', choices=['practical', 'integrated'])
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(prepare(args.cohort, args.destination))

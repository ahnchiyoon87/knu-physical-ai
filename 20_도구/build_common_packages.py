"""Build new timestamped common-plan code bundles, preserving all prior bundles."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from build_checkpoints import ROOT, copy_assets, app_files, put
from build_daily_packages import files, archive
from common_lab_plan import stages


def main():
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    base=ROOT/'10_실습/공통코드'/stamp
    if base.exists():raise ValueError('동일 출력 경로가 있습니다')
    records=[]
    for stage in stages():
        prefix='실' if stage['group']=='실전반' else '통'
        for kind,field in [('start','start_features'),('complete','complete_features')]:
            identity=f'{prefix}{stage["day"]:02d}-{kind}'
            folder=base/identity/'equipment-assistant';features=set(stage[field])
            copy_assets(folder,features)
            if features:app_files(folder,features)
            purpose=('오늘 이전까지의 참고 코드입니다. 오늘 기능은 가이드를 읽으며 직접 만듭니다.' if kind=='start' else
                     '오늘까지의 참고 완성 코드입니다. 자기 결과와 비교할 수 있으며 화면이나 코드가 같을 필요는 없습니다.')
            run=('아직 앱 코드는 없습니다. 자료와 약속을 읽고 첫 서비스를 요청합니다.' if not features else
                 '기본 실행 순서: `uv sync --frozen --extra dev` → `.env.example`을 참고해 자기 `.env` 준비 → `uv run --env-file .env python scripts/bootstrap.py` → `npm.cmd --prefix frontend ci` → `npm.cmd --prefix frontend run build` → `uv run --env-file .env python scripts/serve.py`. 필요한 모델·문서·평가 extra와 DB 준비는 실행 연결 안내를 따릅니다.')
            put(folder,'README.md',f'# {identity} · 두 반 공통 실습\n\n{purpose}\n\n{run}\n\n'
                '자기 프로젝트는 보존하고 새 폴더에서 엽니다. 실제 키와 원시 측정 자료는 포함하지 않습니다. synthetic은 교육용 합성입니다.\n\n'
                '포함 기능: '+(', '.join(sorted(features)) or '코드 없는 뼈대')+'\n\n'
                '모델·DB를 자동으로 실행하지 않습니다. 실제 실행에 필요한 원천·계정·허용한 모델과 비용을 확인합니다.\n')
            owned=files(folder);zip_path=base/(identity+'.zip')
            digest=archive(zip_path,{'equipment-assistant/'+name:folder/name for name in owned},'공통코드')
            records.append({'id':identity,'group':stage['group'],'day':stage['day'],'kind':kind,
                            'keys':stage['keys'],'features':sorted(features),'folder':folder.relative_to(ROOT).as_posix(),
                            'archive':zip_path.relative_to(ROOT).as_posix(),'archive_hash':digest,'files':owned})
    manifest={'stamp':stamp,'records':records,'scope':'공통 가이드 순서의 출발본과 완성본 코드. 학생 완주 미실행; 별도 구조 검사 필요'}
    path=ROOT/'30_기록/공통코드_매니페스트.json'
    if path.exists():
        import shutil
        backup=ROOT/'30_기록/변경전'/('공통코드_'+stamp);backup.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup/path.name)
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    index=['# 공통 실습 코드','', '각 일차의 출발본은 이전 단계, 완성본은 그날까지의 참고 구현입니다. 아래 파일은 공통 가이드 순서에 맞춘 코드이며 실제 학생 완주를 실행한 인증본은 아닙니다.','',
           '| 반 | 일차 | 출발본 | 참고 완성본 |','|---|---|---|---|']
    for s in stages():
        row=[r for r in records if r['group']==s['group'] and r['day']==s['day']]
        links={r['kind']:f'[{r["kind"]}](<{stamp}/{r["id"]}.zip>)' for r in row}
        index.append(f'| {s["group"]} | {s["day"]} | {links["start"]} | {links["complete"]} |')
    (base.parent/'README.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
    print(json.dumps({'bundles':len(records),'files':sum(len(r['files']) for r in records),'output':str(base)},ensure_ascii=False))


if __name__=='__main__':main()

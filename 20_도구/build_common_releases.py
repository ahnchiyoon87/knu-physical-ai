"""Package only each day's guide, prior-stage code and linked theory/resources."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from build_daily_packages import ROOT, archive
from common_lab_plan import THEORY


def main():
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    folder=ROOT/'10_실습/공통배포'/stamp;folder.mkdir(parents=True,exist_ok=False)
    guides=json.loads((ROOT/'30_기록/공통실습가이드_매니페스트.json').read_text(encoding='utf-8'))['records']
    code=json.loads((ROOT/'30_기록/공통코드_매니페스트.json').read_text(encoding='utf-8'))['records']
    theory=json.loads((ROOT/'30_기록/공통강의_매니페스트.json').read_text(encoding='utf-8'))['units']
    records=[]
    for g in guides:
        start=next(c for c in code if c['group']==g['group'] and c['day']==g['day'] and c['kind']=='start')
        assert start['features']==g['start_features']
        identity=start['id'].replace('-start','')
        entries={g['guide']:ROOT/g['guide']}
        for name,digest in start['files'].items():
            path=ROOT/start['folder']/name
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
            entries['프로젝트/equipment-assistant/'+name]=path
        support='10_실습/학생가이드/실행_연결_안내.md';entries[support]=ROOT/support
        for pdf in (ROOT/'실습가이드핸즈온문서').glob('*.pdf'):
            entries[pdf.relative_to(ROOT).as_posix()]=pdf
        if 'quality' in g['keys']:
            for name in ('labeled.csv','labeled_source.json'):
                path=ROOT/'10_실습/공통학생가이드/자료/품질'/name
                entries[path.relative_to(ROOT).as_posix()]=path
        if set(g['keys'])&{'rag','eval'}:
            for name in ('RAG_질문20.json','내_질문30_작성틀.json'):
                path=ROOT/'10_실습/학생가이드/자료'/name
                entries[path.relative_to(ROOT).as_posix()]=path
        theory_units=sorted({n for key in g['keys'] for n in THEORY[key]})
        for n in theory_units:
            u=theory[n-1]
            # Student theory only: narration and future practice solutions are excluded.
            entries[u['deck']]=ROOT/u['deck']
        intro=ROOT/'30_기록/배포_포함목록'/f'공통_{identity}_{stamp}_시작안내.md'
        intro.parent.mkdir(parents=True,exist_ok=True)
        intro.write_text(f'# {g["group"]} {g["day"]}일차\n\n일정: {g["date"]} {g["time"]}\n\n'
            f'1. [오늘 가이드](<{g["guide"]}>)를 엽니다.\n'
            '2. 자기 프로젝트가 잘 이어지면 그대로 사용합니다. 새로 합류하려면 `프로젝트/equipment-assistant` 폴더를 VS Code에서 엽니다.\n'
            '3. [출발 코드 안내](프로젝트/equipment-assistant/README.md)를 읽고 오늘 가이드의 순서대로 진행합니다.\n\n'
            '이 ZIP의 출발 코드는 오늘 이전 단계입니다. 오늘의 참고 완성본은 별도로 공개합니다. 자기 작업을 덮거나 삭제하지 않습니다.\n',encoding='utf-8')
        entries['시작안내.md']=intro
        path=folder/f'{identity}_수업시작.zip'
        digest=archive(path,entries,'공통수업시작')
        records.append({'group':g['group'],'day':g['day'],'date':g['date'],'id':identity,
                        'archive':path.relative_to(ROOT).as_posix(),'archive_hash':digest,'starter':start['id'],
                        'theory_units':theory_units,'files':{name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in entries.items()},
                        'source_paths':{name:p.relative_to(ROOT).as_posix() for name,p in entries.items()}})
    target=ROOT/'30_기록/공통배포_매니페스트.json'
    if target.exists():
        backup=ROOT/'30_기록/변경전'/('공통배포_'+stamp);backup.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup/target.name)
    target.write_text(json.dumps({'stamp':stamp,'records':records,'scope':'당일 가이드·이전 단계 코드·연결 이론·설치 안내. 별도 압축 재추출 검사 필요'},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 일차별 공통 수업 시작 자료','',
           'ESNS에서 해당 일차의 Google Drive 링크로 공개할 로컬 묶음입니다. 파일을 모두 내려받아 미리 공개하는 방식으로 운영하지 않습니다. 실제 업로드나 메시지 전송은 수행하지 않았습니다.','',
           '각 ZIP을 새 폴더에 풀고 `시작안내.md`를 엽니다. 오늘 가이드·출발 코드·연결 이론·설치 안내가 들어 있습니다. 온라인 대본은 강사용 공통 강의 폴더에 있으며 학생 ZIP에는 넣지 않았습니다.','',
           '| 반 | 일차 | 날짜 | 수업 시작 ZIP |','|---|---|---|---|']
    for r in records:lines.append(f'| {r["group"]} | {r["day"]} | {r["date"]} | [다운로드]({stamp}/{r["id"]}_수업시작.zip) |')
    lines+=['','[일차별 참고 완성본](../공통코드/README.md)은 비교하거나 다음 날 합류할 때 구분해 사용합니다. 실제 학생 완주를 실행해 인증한 자료는 아닙니다.','']
    (folder.parent/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'releases':len(records),'stamp':stamp},ensure_ascii=False))


if __name__=='__main__':main()

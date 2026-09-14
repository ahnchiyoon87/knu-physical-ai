"""Make named day completions and separately releasable student packages."""
import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path
from build_checkpoints import ROOT,APP,stages,copy_assets,app_files,put

OUT=ROOT/'10_실습/일차별_완성본'
MANIFEST=ROOT/'30_기록/완성본_매니페스트.json'


def files(folder):
    return {str(p.relative_to(folder)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def archive(path,entries,label):
    if path.exists():raise ValueError('기존 패키지를 덮지 않습니다: '+str(path))
    listing=ROOT/'30_기록/배포_포함목록'/f'{label}_{path.stem}.json'
    listing.parent.mkdir(parents=True,exist_ok=True)
    listing.write_text(json.dumps(sorted(entries),ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,source in sorted(entries.items()):z.write(source,name)
    with zipfile.ZipFile(path) as z:
        if sorted(z.namelist())!=sorted(entries):raise ValueError('ZIP 파일 집합 불일치')
        for name,source in entries.items():
            if hashlib.sha256(z.read(name)).digest()!=hashlib.sha256(source.read_bytes()).digest():
                raise ValueError('ZIP 내용 불일치: '+name)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else []
    for record in old:
        for name,digest in record['files'].items():
            path=ROOT/record['folder']/name
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError('완성본의 사용자 편집 보호: '+str(path))
    start=stages();guides=json.loads((ROOT/'30_기록/실습가이드_매니페스트.json').read_text(encoding='utf-8'))
    checkpoints={r['id']:r for r in json.loads((ROOT/'30_기록/출발본_매니페스트.json').read_text(encoding='utf-8'))}
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S');records=[];releases=[]
    release_root=ROOT/'10_실습/일차별_배포';release_root.mkdir(parents=True,exist_ok=True)
    for group,day,features in start:
        following=next((f for g,d,f in start if g==group and d==day+1),None)
        completed=following if following is not None else features|({'transfer'} if group=='실' else {'agent'})
        folder=OUT/f'{group}{day:02d}-complete'/'equipment-assistant'
        relative=str(folder.relative_to(ROOT)).replace('\\','/')
        previous=next((r for r in old if r['folder']==relative),None)
        if previous:
            for name in previous['files']:(folder/name).unlink(missing_ok=True)
        elif folder.exists() and any(folder.rglob('*')):raise ValueError('기록 없는 출력 폴더: '+str(folder))
        copy_assets(folder,completed);app_files(folder,completed)
        put(folder,'README.md',f'# {group}{day:02d}-complete · 일차 참고 완성 코드\n\n오늘 기능을 비교할 참고 구현입니다. 자신의 결과와 화면이 같을 필요는 없습니다. 다음 일차 합류에는 다음 출발본을 사용합니다.\n\n포함 기능: '+', '.join(sorted(completed))+
            '\n\n설정·DB 준비와 실행 명령은 배포 가이드의 실행 연결 안내를 따릅니다. 실제 키와 원시 측정 데이터는 포함하지 않습니다. 교육용 합성 자료의 출처를 유지합니다. 이 패키지는 코드 작성본이며 학생 실습 완주를 실행해 인증한 파일이 아닙니다.\n')
        included=files(folder);zip_path=OUT/f'{group}{day:02d}-complete_{stamp}.zip'
        digest=archive(zip_path,{'equipment-assistant/'+name:folder/name for name in included},'완성본')
        records.append({'id':f'{group}{day:02d}-complete','features':sorted(completed),'folder':relative,'files':included,
            'archive':str(zip_path.relative_to(ROOT)).replace('\\','/'),'archive_hash':digest})
        guide=next(r for r in guides if r['starter']==f'{group}{day:02d}-start')
        checkpoint=checkpoints[guide['starter']]
        # Preserve relative guide links by keeping the project-relative layout in each release.
        entries={name:ROOT/name for name in [guide['guide'],'10_실습/학생가이드/실행_연결_안내.md','10_실습/학생가이드/합동_OT.md']}
        for name in checkpoint['files']:
            entries['10_실습/일차별_출발본/'+guide['starter']+'/equipment-assistant/'+name]=ROOT/checkpoint['folder']/name
        for pdf in (ROOT/'실습가이드핸즈온문서').glob('*.pdf'):entries[str(pdf.relative_to(ROOT)).replace('\\','/')]=pdf
        if guide['key'] in {'rag','eval'}:
            for path in (ROOT/'10_실습/학생가이드/자료').iterdir():
                if path.is_file():entries[str(path.relative_to(ROOT)).replace('\\','/')]=path
        # Only the day's linked theory is included; no future-day practice solution is present.
        index_path=ROOT/'30_기록/배포_포함목록'/f'{group}{day:02d}_이론목록.md'
        index_path.parent.mkdir(parents=True,exist_ok=True)
        index_path.write_text('# 오늘의 이론\n\n이론 MD와 대본은 강사가 해당 일정에 별도 공개합니다. 이 ZIP은 당일 실습 가이드·출발 코드·설치 안내 묶음입니다.\n',encoding='utf-8')
        entries['00_문서/이론덱/README.md']=index_path
        release=release_root/f'{group}{day:02d}_수업시작_{stamp}.zip'
        rdigest=archive(release,entries,'학생배포')
        releases.append({'id':guide['starter'],'guide':guide['guide'],'archive':str(release.relative_to(ROOT)).replace('\\','/'),
            'archive_hash':rdigest,'files':len(entries),'solution_archive':str(zip_path.relative_to(ROOT)).replace('\\','/')})
    MANIFEST.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'30_기록/배포_매니페스트.json').write_text(json.dumps(releases,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 일차별 공개 파일','', '수업 시작 ZIP은 당일 가이드·이전 단계 출발 코드·설치 안내를 담습니다. 참고 완성본은 별도 파일이며 당일 작업 후 비교하거나 강사가 정한 시점에 공개합니다. ESNS 전송과 Drive 업로드는 수행하지 않았습니다.','',
           '| 일차 | 수업 시작 | 참고 완성본 |','|---|---|---|']
    for item in releases:lines.append(f"| {item['id']} | [{Path(item['archive']).name}]({Path(item['archive']).name}) | [{Path(item['solution_archive']).name}](../일차별_완성본/{Path(item['solution_archive']).name}) |")
    (release_root/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'completions':len(records),'student_releases':len(releases)},ensure_ascii=False))


if __name__=='__main__':main()

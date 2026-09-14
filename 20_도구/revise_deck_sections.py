"""Apply authored application edits only after verifying the current full/part sources."""
import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from build_decks import ROOT,render,slides_for
from deck_content import CAT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('keys',nargs='+');args=parser.parse_args()
    manifest=ROOT/'30_기록/덱_매니페스트.json'
    records=json.loads(manifest.read_text(encoding='utf-8'));selected=[r for r in records if r['key'] in args.keys]
    if set(args.keys)-{r['key'] for r in selected}:raise ValueError('등록되지 않은 덱 키')
    planned=[]
    for record in selected:
        path=ROOT/record['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('전체 덱의 사용자 편집을 보호합니다: '+str(path))
        if path.read_text(encoding='utf-8')!=render(record['meta'],record['key'],record['slides']):
            raise ValueError('이전 렌더 형식과 현재 전체 덱이 다릅니다')
        for number,name in enumerate(record['parts']):
            ids=[s['id'] for s in record['slides'][number*12:(number+1)*12]]
            if (ROOT/name).read_text(encoding='utf-8')!=render(record['meta'],record['key'],record['slides'],ids):
                raise ValueError('분할 파일의 편집을 보호합니다: '+name)
        updated=slides_for(record['meta'],record['key'])
        start=2+len(CAT[record['key']])*3
        changed=[i for i,(before,after) in enumerate(zip(record['slides'],updated)) if before!=after]
        if len(updated)!=len(record['slides']) or any(not start<=i<start+18 for i in changed):
            raise ValueError('요청한 적용 구간 밖 변경입니다')
        planned.append((record,updated,changed))
    backup=ROOT/'30_기록/변경전'/('적용장면_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    for record,_,_ in planned:
        for name in [record['path'],*record['parts']]:
            dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    backup.mkdir(parents=True,exist_ok=True);shutil.copy2(manifest,backup/'덱_매니페스트.json')
    results=[]
    for record,updated,changed in planned:
        (ROOT/record['path']).write_text(render(record['meta'],record['key'],updated),encoding='utf-8')
        for number,name in enumerate(record['parts']):
            ids=[s['id'] for s in updated[number*12:(number+1)*12]]
            (ROOT/name).write_text(render(record['meta'],record['key'],updated,ids),encoding='utf-8')
        record['slides']=updated;record['sha256']=hashlib.sha256((ROOT/record['path']).read_bytes()).hexdigest()
        results.append({'path':record['path'],'changed_slides':[updated[i]['id'] for i in changed]})
    manifest.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    report={'keys':args.keys,'results':results,'backup':str(backup.relative_to(ROOT)),
        'scope':'적용 장면의 핵심 화면 문구와 삽화 보조 지시. 일정·번호·다른 구간 보존'}
    (ROOT/'30_기록/적용장면_변경기록.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()

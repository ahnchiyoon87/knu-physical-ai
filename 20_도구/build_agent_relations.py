"""Append declared educational procedure relationships; do not invent event causes."""
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main(app=None):
    path=(Path(app) if app is not None else ROOT/"10_실습/완성본/equipment-assistant")/"ontology/synthetic.csv"
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    known={(r['source'],r['relation'],r['target']) for r in rows}
    additions=[]
    for lot in range(6):
        additions.append({'source':f'synthetic:worklog:lot:{lot}','source_type':'worklog','relation':'procedure_reference',
            'target':'synthetic:document:FOURM','target_type':'document',
            'provenance':'설계: 변경 여부를 조사할 때 읽을 교육용 절차. 이 LOT에 실제 변경이 있었다는 증거 아님'})
    additions.append({'source':'synthetic:document:FOURM','source_type':'document','relation':'inspection_reference',
        'target':'synthetic:document:FIRST','target_type':'document','provenance':'설계: 교육용 4M 절차와 초물검사 안내의 관련 읽기'})
    for row in additions:
        if (row['source'],row['relation'],row['target']) not in known:rows.append(row)
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    print({'relationships':len(rows),'added_candidates':len(additions)})


if __name__ == "__main__":
    main()

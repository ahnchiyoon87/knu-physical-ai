"""CSV and saved model relationships; no graph database is involved."""
import csv
from collections import deque
from backend.common.config import configured_path,mapping,settings


def relationships(profile):
    path=mapping()['profiles'][profile]['ontology']
    with configured_path(path).open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    required={'source','source_type','relation','target','target_type','provenance'}
    if not rows or set(rows[0])!=required or any(not all(row.values()) for row in rows):
        raise ValueError('관계표의 열·대상 ID·근거를 확인하세요')
    return rows


def load_relationships(path):
    # Validate and read the named table; persistence remains the CSV file at this stage.
    matches=[key for key,value in mapping()['profiles'].items() if value.get('ontology')==path]
    if len(matches)!=1:
        raise ValueError('프로필의 관계표 경로를 확인하세요')
    rows=relationships(matches[0])
    return {'relationships':len(rows),'storage':'CSV 관계표','nodes':sorted({r[k] for r in rows for k in ('source','target')})}


def paths(start,end):
    all_rows=[]
    for profile,config in mapping()['profiles'].items():
        if config.get('ontology') and configured_path(config['ontology']).is_file():
            with configured_path(config['ontology']).open(encoding='utf-8-sig',newline='') as stream:
                all_rows+=list(csv.DictReader(stream))
    edges={};kinds={}
    for row in all_rows:
        for left,right in [('source','target'),('target','source')]:
            edges.setdefault(row[left],[]).append((row[right],row))
            kinds[row[left]]=row[left+'_type']
    if start not in edges or end not in edges:return []
    queue=deque([(start,[start],[])])
    visited={start}
    while queue:
        current,nodes,relations=queue.popleft()
        if current==end:
            return [{'nodes':[{'id':n,'kind':kinds[n]} for n in nodes],
                     'relations':[{'kind':r['relation'],'provenance':r['provenance']} for r in relations]}]
        if len(relations)>=settings()['agent']['max_graph_hops']:continue
        for following,row in edges[current]:
            if following not in visited:
                visited.add(following);queue.append((following,nodes+[following],relations+[row]))
    return []


def flush_outbox():
    return {'applied':0,'remaining':None,'status':'not_applicable',
            'reason':'현재 단계는 CSV 관계표입니다. 그래프 DB 반영은 RAG 일차에서 추가합니다.'}

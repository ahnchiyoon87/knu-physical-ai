"""실제 Neo4jVector 경로와 과제 검색의 결과를 대조한다. offline 환경 전용."""
from pathlib import Path
import importlib.util
import json
from hydops.config import SETTINGS
from hydops.b6_sop.search import search_sop

ROOT = Path('/course')


def main():
    if SETTINGS.agent_mode != 'offline':
        raise RuntimeError('offline 환경에서만 실행합니다.')
    output = ROOT/'작업기록/다섯째날제작_20260915/실제검색.json'
    if output.exists():
        raise FileExistsError(output)
    path = ROOT/'실습자료/5일차/완성본/practical/search_lab.py'
    spec = importlib.util.spec_from_file_location('search_lab_verify', path)
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)
    cases = []
    keys = lambda result: {(h['doc_id'], h['version'], h['section']) for h in result['hits']}
    for asset, kind in [('HYD-01','COOLING_ANOMALY'),('HYD-02','COOLING_ANOMALY'),('HYD-03','COOLING_ANOMALY'),('HYD-01','SENSOR_FAULT')]:
        actual = lab.search_sop_lab(asset, kind)
        reference = search_sop(asset, kind)
        assert keys(actual) == keys(reference), (asset, kind, keys(actual), keys(reference))
        proposal = lab.offline_proposal(asset, kind)
        cases.append({'asset': asset, 'type': kind, 'lab': actual, 'platform': reference, 'proposal': proposal})
    assert cases[2]['lab']['hits'] == [] and cases[2]['proposal']['final']['decision'] == 'HOLD'
    assert cases[3]['proposal']['final']['decision'] == 'SENSOR_CHECK'
    output.write_text(json.dumps({'scope': '실제 Neo4jVector+HashEmbeddings 검색 경로. 유료 임베딩/LLM 품질·학생 완주 검증 아님.', 'cases': cases}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([{'asset': c['asset'], 'type': c['type'], 'hits': len(c['lab']['hits']), 'decision': c['proposal']['final']['decision']} for c in cases], ensure_ascii=False))


if __name__ == '__main__':
    main()

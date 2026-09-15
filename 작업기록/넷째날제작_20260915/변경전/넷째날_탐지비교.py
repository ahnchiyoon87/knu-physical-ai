"""원문 4일차 비교를 실제 데이터에서 실행한다. 컨테이너 내부 실행용."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
from hydops.b5_detect import evaluate

ROOT = Path('/course')


def main():
    output = ROOT/'작업기록/넷째날제작_20260915/탐지비교.json'
    if output.exists():
        raise FileExistsError(output)
    file = ROOT/'실습자료/4일차/완성본/practical/detector_lab.py'
    spec = importlib.util.spec_from_file_location('day4_compare', file)
    lab = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = lab
    spec.loader.exec_module(lab)
    ids = lab.fixed_test_ids()
    table = lab.compare_sustain()
    limits = []
    for delta in (1.0, 3.0):
        params = dict(k_sigma=4.0, min_delta_c=delta, sustain_s=10, smooth_s=5)
        result = evaluate.evaluate(**params)
        limits.append({'params': params, 'result': result})
    boundary_rows = lab.simulate_rows(300, 0.5, seed=7)
    boundary = [dict(sustain_s=s, **lab.run_stream(boundary_rows, lab.SustainDetector(sustain_s=s), lab.EventBook())) for s in (1, 5, 10, 20)]
    record = {
        'scope': 'UCI固定시험 구간 실제 평가와 메모리 합성 스트림. DB/관제UI/LLM/학생 완주 검증 아님.',
        'source_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
        'test_ids': ids, 'sustain_comparison': table,
        'limit_comparison': limits, 'boundary_stream': boundary,
    }
    record['scope'] = record['scope'].replace('固定', ' 고정 ')
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'sustain': table, 'limit': [{'min_delta_c': r['params']['min_delta_c'], 'fp': r['result']['fp'], 'delay': r['result']['mean_delay_s']} for r in limits], 'boundary': boundary}, ensure_ascii=False))


if __name__ == '__main__':
    main()

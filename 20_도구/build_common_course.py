"""Build one shared content edition; preserve the original cohort editions.

No model calls or lab execution. Content edition is not a recording-time claim.
"""
import copy
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from deck_content import CAT
from common_course_editorial import TRANSITIONS, FIRST_TERMS
from common_worked_examples import WORKED

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '00_문서/공통강의'
MANIFEST = ROOT / '30_기록/공통강의_매니페스트.json'
UNITS = [
 ('데이터의 뜻과 품질', 'AB', '표를 읽을 때 값과 단위, 원천과 LOT의 의미를 확인합니다.', '계산할 자료의 뜻을 확인했으니 결과를 보여 주고 판별하는 방법으로 이어갑니다.'),
 ('시각화와 표 데이터 판별', 'CF', '같은 근거에서 차트와 설명을 만들고 판별 모델의 입력과 정답을 구별합니다.', '개별 결과를 판별했으니 시간에 따라 달라지는 값을 살펴보겠습니다.'),
 ('규칙과 시계열 변화', 'DH', '생산 조건에 맞는 규칙과 시간 구간을 사용해 변화를 찾습니다.', '변화를 찾는 기준을 배웠습니다. 다음에는 반복 실행할 처리 흐름과 모델 비교를 연결합니다.'),
 ('파이프라인과 모델 비교', 'EN', '적재부터 결과 저장까지 연결하고 단순 기준선과 모델의 차이를 같은 조건으로 평가합니다.', '수치 처리의 연결과 비교 기준을 만들었습니다. 다음에는 이미지와 수명처럼 입력과 목표가 다른 모델 문제를 살펴보겠습니다.'),
 ('이미지 이상과 남은 수명', 'GI', '이미지의 이상 점수와 수명 예측이 각각 어떤 자료와 정답을 필요로 하는지 확인합니다.', '입력과 목표가 다른 문제를 구별했습니다. 다음에는 문서와 관계를 답의 근거로 연결합니다.'),
 ('문서와 관계를 근거로 답하기', 'J', '검색된 문서와 표, 관계가 답의 어떤 주장을 지지하는지 확인합니다.', '답을 만드는 경로를 확인했으니 평가하고 실행 환경을 옮기는 조건을 살펴보겠습니다.'),
 ('응답 평가와 서비스 배포', 'KL', '질문셋의 결과와 서비스 상태를 구별하고 저장소와 권한, 재시작 조건을 확인합니다.', '근거와 실행 상태를 읽을 수 있게 됐습니다. 이제 제안과 승인된 변경을 재관측으로 이어갑니다.'),
 ('도구와 승인, 재관측', 'OP', '도구의 책임과 승인 범위를 정하고 변경 뒤 확인한 결과를 다음 판단에 사용합니다.', '다른 문제에서도 입력·목표·근거·허용 행동을 다시 정해 자기 서비스를 만듭니다.'),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_script(text):
    sections = re.split(r'^## (S\d+) · [^\n]+\n', text, flags=re.M)
    result = {}
    for index in range(1, len(sections), 2):
        body = sections[index + 1]
        result[sections[index]] = body.split('### 발화\n', 1)[1].split('### 다음 장으로', 1)[0].strip()
    return result


def render(title, slides, script=False):
    lines = [f'# {title}' + (' · 온라인 이론 대본' if script else ' · 공통 이론 덱'), '',
             '실전반(4학년)과 통합반이 함께 사용하는 내용입니다.', '',
             '제작 상태: 공통 내용 집필본. 회차별 시간 배분과 전체 흐름을 검토 중입니다. 표시한 장수는 녹화 분량의 증거가 아닙니다.', '']
    if not script:
        lines += ['삽화는 해당 장의 대상·관계·조건을 정확히 보여 주는 독창적인 장면으로 제작합니다. 아래 지시는 실제 사진이나 실측 화면의 증거가 아닙니다. 표지나 중복 목차를 임의 추가하지 않습니다.', '']
    for s in slides:
        lines += [f'## {s["id"]} · {s["title"]}', '']
        if script:
            lines += ['### 발화', '', s['spoken'], '', '### 다음 장으로', '', s['bridge'], '']
        else:
            lines += ['**화면 문구**', '', '\n\n'.join(s['screen']), '',
                      '**삽화·구성** ' + s['visual'], '', '**이 장의 결론** ' + s['conclusion'], '',
                      '**다음 장 연결** ' + s['bridge'], '', '**근거·성격** ' + s['evidence'], '']
    return '\n'.join(lines)


def main():
    previous = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {'files': {}}
    for name, expected in previous['files'].items():
        if not (ROOT / name).exists() or digest(ROOT / name) != expected:
            raise ValueError('공통 원고의 현재 편집을 보호합니다: ' + name)
    decks = json.loads((ROOT / '30_기록/덱_매니페스트.json').read_text(encoding='utf-8'))
    scripts = json.loads((ROOT / '30_기록/대본_매니페스트.json').read_text(encoding='utf-8'))['written']
    sources = {}
    for deck in decks:
        if deck['key'] == 'M' or deck['key'] in sources:
            continue
        if digest(ROOT / deck['path']) != deck['sha256']:
            raise ValueError('기존 덱의 변경을 먼저 반영하세요: ' + deck['path'])
        script = next(s for s in scripts if s['key'] == deck['key'] and s['group'] == deck['meta']['반'])
        if digest(ROOT / script['path']) != script['hash']:
            raise ValueError('기존 대본의 변경을 먼저 반영하세요: ' + script['path'])
        sources[deck['key']] = (deck, script, extract_script((ROOT / script['path']).read_text(encoding='utf-8')))
    assert set(sources) == set(''.join(u[1] for u in UNITS))
    planned = {}; units = []; provenance = []
    for number, (title, keys, opening, closing) in enumerate(UNITS, 1):
        slides = []
        for key in keys:
            deck, script, spoken = sources[key]
            if slides and key in TRANSITIONS:
                heading, screen, visual, words = TRANSITIONS[key]
                slides.append({'title': heading, 'screen': screen, 'visual': visual, 'spoken': words,
                               'conclusion': screen[-1], 'bridge': deck['slides'][2]['title'],
                               'evidence': '공통 순서의 개념 연결을 위한 교육용 설계', 'transition_to': key})
            end = 2 + len(CAT[key]) * 3 + 18 + 6
            for source_slide in deck['slides'][2:end]:
                s = copy.deepcopy(source_slide)
                s.pop('seconds', None)  # Previous nominal minutes are not measured narration.
                s['source_id'] = s['id']; s['source_key'] = key
                s['id'] = f'U{number:02}-S{len(slides)+2:03}'
                s['spoken'] = spoken[source_slide['id']].replace('다음 영상에서는', '다음 구간에서는').replace('다음 영상에서', '다음 구간에서')
                term = FIRST_TERMS.get((key, source_slide['id']))
                if term:
                    s['screen'].insert(0, term)
                    s['spoken'] = term + '\n\n' + s['spoken']
                slides.append(s)
            provenance.append({'unit': number, 'key': key, 'deck': deck['path'], 'deck_sha256': deck['sha256'],
                               'script': script['path'], 'script_sha256': script['hash'], 'source_range': [deck['slides'][2]['id'], deck['slides'][end-1]['id']]})
            for example_number, example in enumerate(WORKED.get(key, []), 1):
                item=copy.deepcopy(example)
                item.update(source_key=key,worked_example=example_number)
                slides.append(item)
        first = {'id': f'U{number:02}-S001', 'title': title, 'screen': [opening, '결과와 함께 입력·판단 기준·근거를 확인합니다.'],
                 'visual': '이 단위의 두 입력과 결과를 하나의 구체적인 작업 장면으로 연결한다. 서로 다른 원천을 같은 사건인 것처럼 그리지 않는다.',
                 'conclusion': opening, 'bridge': slides[0]['title'], 'evidence': '공통 과정 설계',
                 'spoken': opening + '\n\n이번 단위에서는 화면에 나온 판단을 순서대로 살펴보겠습니다. 각 결과가 어떤 입력에서 나왔는지 확인하고, 그 결과만으로 알 수 없는 범위도 함께 남깁니다.'}
        last = {'id': f'U{number:02}-S{len(slides)+2:03}', 'title': '확인한 결과를 다음 판단에 넘깁니다',
                'screen': [opening, closing], 'visual': '앞 장면에서 확인한 기록과 다음 작업에 넘길 근거를 구체적인 문서와 화면으로 연결한다. 확인되지 않은 칸은 임의로 채우지 않는다.',
                'conclusion': closing, 'bridge': closing, 'evidence': '공통 과정 설계',
                'spoken': opening + '\n\n각 사례에서 확인한 사실과 추가로 필요한 근거를 구별했습니다. ' + closing}
        slides = [first, *slides, last]
        for i, slide in enumerate(slides, 1):
            slide['id'] = f'U{number:02}-S{i:03}'
        for i, slide in enumerate(slides[:-1]):
            if i and slide.get('source_key') != slides[i+1].get('source_key'):
                slide['bridge'] = slide['conclusion'] + ' 다음에는 ' + slides[i+1]['title'] + '로 이어갑니다.'
        folder = OUT / f'{number:02}_{title}'
        deck_path = folder / '이론덱.md'; script_path = folder / '온라인대본.md'
        references = []
        for key in keys:
            original = (ROOT / sources[key][0]['path']).read_text(encoding='utf-8')
            references.append(original.split('\n## 출처', 1)[1])
        footer = '\n\n## 제작 참고 출처\n\n' + '\n\n'.join(references)
        planned[deck_path] = render(title, slides) + footer
        planned[script_path] = render(title, slides, True)
        parts = []
        for start in range(0, len(slides), 12):
            path = folder / 'NotebookLM_분할' / f'{start//12+1:02}.md'
            planned[path] = render(title, slides[start:start+12]) + footer
            parts.append(path.relative_to(ROOT).as_posix())
        units.append({'unit': number, 'title': title, 'keys': list(keys), 'slides': slides,
                      'deck': deck_path.relative_to(ROOT).as_posix(), 'script': script_path.relative_to(ROOT).as_posix(), 'parts': parts})
    index = ['# 두 반 공통 강의', '', '실전반(4학년)과 통합반은 아래의 같은 덱과 온라인 이론 대본을 사용합니다. 기존 반별 초안에서 공통 내용을 추출해 연결한 집필본이며 회차별 배포·시간 배분, 실습가이드와 출발본 전환은 진행 중입니다.', '',
             '| 단위 | 이론 덱 | 온라인 대본 | 장수 |', '|---|---|---|---:|']
    for u in units:
        folder = Path(u['deck']).parent.relative_to('00_문서/공통강의').as_posix()
        index.append(f'| {u["unit"]}. {u["title"]} | [덱](<{folder}/이론덱.md>) | [대본](<{folder}/온라인대본.md>) | {len(u["slides"])} |')
    index += ['', '기존 반별 덱은 보존된 원고입니다. 같은 주제를 다시 고칠 때 공통 원고와 기존 제작 소스의 차이를 먼저 확인합니다. 기존의 4H 표시는 새 공통 원고의 측정 길이로 승계하지 않았습니다.', '']
    planned[OUT / 'README.md'] = '\n'.join(index)
    for path in planned:
        if path.exists() and path.relative_to(ROOT).as_posix() not in previous['files']:
            raise ValueError('관리하지 않는 기존 파일을 덮지 않습니다: ' + str(path))
    modified = [p for p, text in planned.items() if p.exists() and p.read_text(encoding='utf-8') != text]
    if modified:
        backup = ROOT / '30_기록/변경전' / ('공통원고_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
        for p in modified:
            dest = backup / p.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
        if MANIFEST.exists():
            shutil.copy2(MANIFEST, backup / MANIFEST.name)
    for path, text in planned.items():
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding='utf-8')
    record = {'status': '공통 내용 집필본; 시간·선수 개념·실습·일정 전환 검토 중', 'units': units, 'sources': provenance,
              'editorial_sources': {f'20_도구/{name}': digest(ROOT/'20_도구'/name) for name in ('common_course_editorial.py','common_worked_examples.py')},
              'cohorts': {'실전반(4학년)': [u['deck'] for u in units], '통합반(2·3학년)': [u['deck'] for u in units]},
              'files': {p.relative_to(ROOT).as_posix(): digest(p) for p in planned}}
    MANIFEST.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'units': len(units), 'slides': sum(len(u['slides']) for u in units), 'files': len(planned)}, ensure_ascii=False))


if __name__ == '__main__':
    main()

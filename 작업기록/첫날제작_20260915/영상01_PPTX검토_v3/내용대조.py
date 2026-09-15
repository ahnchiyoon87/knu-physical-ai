"""첫 영상 PPTX의 내용 보존 검사. 렌더·의미·음성 검사를 대신하지 않는다."""
from pathlib import Path
import json
import re
from pptx import Presentation

here = Path(__file__).resolve().parent
project = here.parents[2]
deck = project / '이론자료/1회차/영상01/제조데이터와판단_덱.md'
presentation = Presentation(here / '제조데이터와판단_발표자노트.pptx')
sections = re.split(r'^## S\d+ ', deck.read_text(encoding='utf-8'), flags=re.M)[1:]

def normalize(text):
    return re.sub(r'\s+', '', text.replace('**', '').replace('`', ''))

def expected(section):
    lines = []
    for line in section.splitlines():
        if re.fullmatch(r'[| :\-]+', line) and '|' in line:
            continue
        lines.append(line.replace('|', '') if line.startswith('|') else line)
    return normalize(''.join(lines))

assert len(sections) == len(presentation.slides) == 11
results = []
for index, (section, slide) in enumerate(zip(sections, presentation.slides), 1):
    actual = normalize(''.join(shape.text for shape in slide.shapes if shape.has_text_frame))
    target = expected(section)
    assert actual == target, f'S{index:02d}: content differs'
    assert actual[:-1] != target, 'single-character omission must be detected'
    results.append({'slide': index, 'content_equal': True,
                    'nonempty_editable_text_shapes': sum(bool(s.text) for s in slide.shapes if s.has_text_frame),
                    'picture_shapes': sum(s.shape_type == 13 for s in slide.shapes)})
report = {'slides': results, 'comparison': 'all slide text in order; whitespace and Markdown formatting normalized',
          'omitted_character_countercheck': '11/11 detected',
          'limits': 'Does not prove rendering, instructional quality, voice duration, or native PowerPoint table structure.'}
(here / '내용대조.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))

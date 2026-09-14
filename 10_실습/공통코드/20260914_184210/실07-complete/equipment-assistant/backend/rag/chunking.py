"""Markdown table rows keep their own header; prose chunks preserve section identity."""
import re


def chunk_markdown(text: str, max_chars: int, overlap: int) -> list[dict]:
    if max_chars < 100 or not 0 <= overlap < max_chars // 2:
        raise ValueError("조각 크기와 겹침 범위를 확인하세요")
    chunks, section, paragraph = [], "본문", []

    def flush():
        joined = "\n".join(paragraph).strip()
        paragraph.clear()
        while joined:
            if len(joined) <= max_chars:
                chunks.append({"section": section, "body": joined})
                break
            end = joined.rfind(" ", max_chars // 2, max_chars)
            if end < 0:
                end = max_chars
            chunks.append({"section": section, "body": joined[:end]})
            joined = joined[max(1, end - overlap):].lstrip()

    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("#"):
            flush()
            section = line.lstrip("# ").strip()
        elif (index + 1 < len(lines) and "|" in line
              and re.fullmatch(r"\s*\|?[\s:|\-]+\|?\s*", lines[index + 1])):
            flush()
            header = line.strip()
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                body = header + "\n" + lines[index].strip()
                if len(body) > max_chars:
                    raise ValueError("한 표 행과 머리글이 조각 상한보다 큽니다. 열/문서 구성을 먼저 확인하세요")
                chunks.append({"section": section, "body": body})
                index += 1
            continue
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
        index += 1
    flush()
    return chunks


def reciprocal_rank_fusion(vector_ids: list[str], lexical_ids: list[str], constant: int) -> list[str]:
    if constant < 1:
        raise ValueError("순위 결합 상수는 양수여야 합니다")
    scores = {}
    for ranking in (vector_ids, lexical_ids):
        for rank, identity in enumerate(dict.fromkeys(ranking), 1):
            scores[identity] = scores.get(identity, 0.0) + 1 / (constant + rank)
    return sorted(scores, key=lambda identity: (-scores[identity], identity))

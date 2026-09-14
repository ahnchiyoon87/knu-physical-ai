"""Expected evidence and status checks remain separate from model judgements."""
from backend.common.response import reply
from backend.common.service import fingerprint
from backend.rag import service as rag

from . import gateway


def score_contract(case: dict, response: dict) -> dict:
    actual = {item.get("document_id") for item in response["evidence"] if item["kind"] == "doc"}
    expected = set(case.get("expected_documents", []))
    claim_ids = [index for claim in response.get("answer") or [] if isinstance(claim, dict)
                 for index in claim.get("evidence_ids", [])]
    numbered = {item.get("id") for item in response["evidence"]}
    checks = {
        "status": response["status"] in case["expected_statuses"],
        "current_documents": all(item.get("status") == "current" for item in response["evidence"] if item["kind"] == "doc"),
        "expected_evidence": expected.issubset(actual),
        "valid_citation_ids": all(index in numbered for index in claim_ids),
        "nonempty_answer_has_evidence": response["status"] != "ok" or bool(response["evidence"]),
    }
    return {"checks": checks, "passed": sum(checks.values()), "total": len(checks),
            "semantic_judgement": "미판정: 계약 검사만으로 주장 지지와 정답을 확정하지 않음"}


def validate_cases(cases: list[dict],require_reference: bool=False):
    if not cases or len(cases) > 100:
        raise ValueError("질문셋은 1~100개입니다")
    valid_statuses={"ok","none","refused","failed","error","pending_approval","insufficient"}
    for case in cases:
        if not isinstance(case,dict) or not all(isinstance(case.get(k),str) and case[k].strip() for k in ('id','question')):
            raise ValueError("질문 ID와 질문을 먼저 작성하세요")
        if not isinstance(case.get('expected_documents'),list) or any(not isinstance(x,str) or not x for x in case['expected_documents']):
            raise ValueError("기대 문서 ID는 문자열 배열이어야 합니다")
        if not isinstance(case.get('expected_statuses'),list) or not case['expected_statuses'] or not set(case['expected_statuses'])<=valid_statuses:
            raise ValueError("기대 응답 상태를 먼저 작성하세요")
        if require_reference and 'ok' in case['expected_statuses'] and not str(case.get('reference','')).strip():
            raise ValueError("RAGAS 전에 사람이 작성한 reference가 필요합니다")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("질문 ID가 중복됩니다")


def run(rid: str, profile: str, provider: str, cases: list[dict]):
    validate_cases(cases)
    results = []
    for case in cases:
        result = rag.ask(rid, profile, case["question"], provider)
        encoded = result.model_dump(mode="json")
        scores = score_contract(case, encoded)
        results.append({"case_id": case["id"], "question": case["question"], "result": encoded, "contract": scores})
    identity = fingerprint([rid, profile, provider, cases])
    answer = {"id": identity, "profile": profile, "provider": provider, "question_set_hash": fingerprint(cases),
              "results": results, "scope": "검색·답변 실행 및 계약 검사. RAGAS 모델 심사는 별도 실행"}
    gateway.save(identity, rid, provider, answer)
    return reply(rid, answer)


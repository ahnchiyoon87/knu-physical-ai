"""Connections and configured JSON-only model requests."""
import json
import os
from contextlib import contextmanager
from time import perf_counter

import httpx
import psycopg
from psycopg.rows import dict_row

from .config import env, settings
from .log import emit


@contextmanager
def database(*, readonly=False):
    key = "READONLY_DATABASE_URL" if readonly else "DATABASE_URL"
    with psycopg.connect(env(key), row_factory=dict_row) as connection:
        if readonly:
            connection.execute("SET TRANSACTION READ ONLY")
        timeout = settings()["service"]["statement_timeout_ms"] if readonly else settings()["service"].get("write_timeout_ms", 300000)
        connection.execute("SELECT set_config('statement_timeout', %s, true)", (str(timeout),))
        yield connection


def model_json(provider: str, instruction: str, payload: dict, schema: dict, *, layer: str, step: str):
    if os.getenv("ALLOW_MODEL_CALLS", "false").lower() != "true":
        raise ValueError("모델 호출이 꺼져 있습니다. 실행 의도를 확인하고 ALLOW_MODEL_CALLS를 설정하세요")
    providers = settings()["models"]
    if provider not in providers:
        raise ValueError("등록되지 않은 모델 공급자입니다")
    config = providers[provider]
    name, base, key = env(config["name_env"]), env(config["base_url_env"]), env(config["key_env"])
    body = json.dumps({k: v for k, v in payload.items() if v is not None and v != "" and v != []},
                      ensure_ascii=False, allow_nan=False)
    if len(instruction) + len(body) > config["max_input_chars"]:
        raise ValueError("설정한 입력 문자 상한 초과: 자르지 않았습니다. 근거와 질문 범위를 확인하세요")
    request = {"model": name, "messages": [{"role": "system", "content": instruction},
               {"role": "user", "content": body}], "temperature": 0,
               "max_tokens": config["max_output_tokens"],
               "response_format": {"type": "json_schema", "json_schema": {
                   "name": "result", "strict": True, "schema": schema}}}
    started = perf_counter()
    try:
        with httpx.Client(timeout=config["timeout_seconds"]) as client:
            response = client.post(base.rstrip("/") + "/chat/completions", json=request,
                                   headers={"Authorization": f"Bearer {key}"})
            response.raise_for_status()
            result = response.json()
        choice = result["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("모델 응답이 정상 종료되지 않았습니다")
        content = json.loads(choice["message"]["content"])
    except Exception as exc:
        emit(layer, step, "backend/common/gateway.py:model_json", status="failed",
             ms=(perf_counter() - started) * 1000, model=name, reason=type(exc).__name__)
        raise
    usage = result.get("usage", {})
    tokens_in, tokens_out = usage.get("prompt_tokens"), usage.get("completion_tokens")
    prices = config["input_usd_per_million"], config["output_usd_per_million"]
    cost = None if None in (tokens_in, tokens_out, *prices) else (
        tokens_in * prices[0] + tokens_out * prices[1]) / 1_000_000
    metrics = {"model": name, "tokens_in": tokens_in, "tokens_out": tokens_out,
               "cost_usd": cost, "request_ms": round((perf_counter() - started) * 1000, 3),
               "warnings": [] if cost is not None else ["요금 또는 사용량 정보가 없어 비용은 미측정입니다"]}
    emit(layer, step, "backend/common/gateway.py:model_json", ms=metrics["request_ms"],
         model=name, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost,
         inputs={"chars": len(body)}, outputs={"fields": len(content)})
    return content, metrics

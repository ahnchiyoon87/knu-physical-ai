"""Small shared contracts: stable identifiers and finite numbers."""
import hashlib
import json
import math


def fingerprint(value) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def finite_number(value, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"유한한 수가 아닙니다: {label}")
    return result


def combine_metrics(calls: list[dict]) -> dict:
    result={"model":", ".join(dict.fromkeys(call["model"] for call in calls)),"calls":calls,
            "warnings":list(dict.fromkeys(w for call in calls for w in call.get("warnings",[])))}
    for field in ("tokens_in","tokens_out","cost_usd","request_ms"):
        values=[call.get(field) for call in calls]
        result[field]=sum(values) if all(value is not None for value in values) else None
    return result

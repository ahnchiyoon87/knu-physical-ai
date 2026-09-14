"""Append request-scoped metadata, never raw documents or credentials."""
import json
import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter

from .config import ROOT

request_id = ContextVar("request_id", default="startup")
_lock = Lock()


def emit(layer: str, step: str, loc: str, *, status="ok", ms=0.0, inputs=None, outputs=None, **metrics):
    row = {"ts": datetime.now(UTC).isoformat(), "rid": request_id.get(), "layer": layer,
           "step": step, "loc": loc, "status": status, "ms": round(ms, 3),
           "in": inputs or {}, "out": outputs or {}, **metrics}
    folder = ROOT / "logs"
    folder.mkdir(exist_ok=True)
    with _lock, (folder / "app.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    if os.getenv("PORT"):
        # Cloud Run captures stdout in Cloud Logging; the local file is only a current-instance view.
        sys.stdout.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
        sys.stdout.flush()


@contextmanager
def span(layer, step, loc, **inputs):
    started = perf_counter()
    output = {}
    try:
        yield output
    except Exception as exc:
        emit(layer, step, loc, status="failed", ms=(perf_counter() - started) * 1000,
             inputs=inputs, reason=type(exc).__name__)
        raise
    else:
        emit(layer, step, loc, ms=(perf_counter() - started) * 1000, inputs=inputs, outputs=output)


def trace(rid: str) -> list[dict]:
    path = ROOT / "logs/app.jsonl"
    if not path.exists():
        return []
    with _lock, path.open(encoding="utf-8") as stream:
        return [row for line in stream if (row := json.loads(line))["rid"] == rid]


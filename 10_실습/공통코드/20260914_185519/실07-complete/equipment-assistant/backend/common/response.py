"""One response envelope for every service boundary."""
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Status = Literal["ok", "none", "refused", "failed", "error", "pending_approval", "insufficient"]


class Response(BaseModel):
    rid: str
    status: Status
    answer: Any = None
    evidence: list[dict] = Field(default_factory=list)
    reason: str = ""
    meta: dict = Field(default_factory=lambda: {"warnings": []})

    @model_validator(mode="after")
    def reason_is_explicit(self):
        if self.status != "ok" and not self.reason:
            raise ValueError("ok 외의 응답에는 reason이 필요합니다")
        return self


def reply(rid: str, answer=None, *, status: Status = "ok", evidence=None, reason="", meta=None) -> Response:
    return Response(rid=rid, answer=answer, status=status, evidence=evidence or [], reason=reason,
                    meta=meta or {"warnings": []})


"""DeepEval contract metric checks stored responses without another model request."""
import os

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT","YES")
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

from .service import score_contract


class ContractMetric(BaseMetric):
    def __init__(self):
        self.threshold=1.0
        self.score=None
        self.success=False
        self.reason="측정 전"
        self.error=None
        self.evaluation_cost=0.0
        self.async_mode=False
        self.strict_mode=True
        self.verbose_mode=False

    @property
    def __name__(self):
        return "Evidence and state contract"

    def measure(self,test_case,**kwargs):
        metadata=test_case.additional_metadata
        result=score_contract(metadata["case"],metadata["response"])
        self.score=result["passed"]/result["total"]
        self.success=self.score>=self.threshold
        self.reason=", ".join(name for name,passed in result["checks"].items() if not passed) or "계약 항목 일치"
        return self.score

    async def a_measure(self,test_case,**kwargs):
        return self.measure(test_case,**kwargs)

    def is_successful(self):
        return self.success


def regression(case: dict,response: dict):
    test_case=LLMTestCase(input=case["question"],actual_output=str(response["answer"]),
                         additional_metadata={"case":case,"response":response})
    metric=ContractMetric()
    metric.measure(test_case)
    return {"name":metric.__name__,"score":metric.score,"passed":metric.success,"reason":metric.reason,
            "model_calls":0,"semantic_correctness":"미판정"}

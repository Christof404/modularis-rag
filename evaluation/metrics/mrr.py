from ..core.base_interfaces import BasePerformanceMetric, Metric
from typing import List, Tuple


class MRR(BasePerformanceMetric):
    def __init__(self):
        super().__init__(name="mrr")

    def evaluate(self, retrieved: Tuple[str, ...], expected: Tuple[str, ...], at_k: List[int]) -> List[Metric]:
        result = []
        for k in at_k:
            mrr = 0.0
            retrieved_k = retrieved[:k]
            for rank, doc_id in enumerate(retrieved_k, start=1):
                if doc_id in expected:
                    mrr = 1.0 / rank
                    break
            result.append(Metric(k=k, result=mrr))

        return result

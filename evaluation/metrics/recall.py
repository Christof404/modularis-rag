from ..core.base_interfaces import BasePerformanceMetric, Metric
from typing import List, Tuple


class Recall(BasePerformanceMetric):
    def __init__(self):
        super().__init__(name="recall")

    def evaluate(self, retrieved: Tuple[str, ...], expected: Tuple[str, ...], at_k: List[int]) -> List[Metric]:
        result = []
        for k in at_k:
            retrieved_k = retrieved[:k]

            matches_k = [doc_id for doc_id in retrieved_k if doc_id in expected]
            recall = len(matches_k) / len(expected) if expected else 0.0

            result.append(Metric(k=k, result=recall))

        return result

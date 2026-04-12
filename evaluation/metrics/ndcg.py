from ..core.base_interfaces import BasePerformanceMetric, Metric
from typing import List, Tuple
import numpy as np


class NDCG(BasePerformanceMetric):
    def __init__(self):
        super().__init__(name="ndcg")

    def evaluate(self, retrieved: Tuple[str, ...], expected: Tuple[str, ...], at_k: List[int]) -> List[Metric]:
        result = []
        for k in at_k:
            dcg = 0.0
            retrieved_k = retrieved[:k]
            for rank, doc_id in enumerate(retrieved_k, start=1):
                if doc_id in expected:
                    dcg += 1.0 / np.log2(rank + 1)

            i_dcg = 0.0
            for rank in range(1, min(len(expected), k) + 1):
                i_dcg += 1.0 / np.log2(rank + 1)

            ndcg = dcg / i_dcg if i_dcg > 0 else 0.0
            result.append(Metric(k=k, result=ndcg))

        return result

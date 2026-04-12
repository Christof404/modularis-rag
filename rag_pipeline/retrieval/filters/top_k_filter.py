from ...core.models import ScoredChunk
from ..interfaces import BaseFilter
from typing import List


class TopKFilter(BaseFilter):
    def __init__(self, top_k: int = 5, **kwargs):
        """
        :param min_score: The minimum cosine similarity score (0.0 to 1.0)
        """
        super().__init__(**kwargs)
        self.top_k = top_k

    def process(self, chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        # sort chunks highes to lowest
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:self.top_k]

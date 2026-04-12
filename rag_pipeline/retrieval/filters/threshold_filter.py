from ...core.models import ScoredChunk, ChunkStatus
from ..interfaces import BaseFilter
from typing import List


class ScoreThresholdFilter(BaseFilter):
    def __init__(self, min_score: float = 0.5, **kwargs):
        """
        :param min_score: The minimum cosine similarity score (0.0 to 1.0)
        """
        super().__init__(**kwargs)
        self.min_score = min_score

    def process(self, chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        filtered_chunks = []

        for chunk in chunks:
            if chunk.score >= self.min_score:
                filtered_chunks.append(chunk)
            else:
                chunk.status = ChunkStatus.FILTERED_BY_THRESHOLD

        return filtered_chunks

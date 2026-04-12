from ...core.models import ScoredChunk, ChunkStatus
from collections import defaultdict
from ..interfaces import BaseFilter
from typing import List


class SourceDiversityFilter(BaseFilter):
    def __init__(self, max_chunks_per_source: int = 3, **kwargs):
        """
        :param max_chunks_per_source: What is the maximum number of chunks from the same article?  (based on metadata.title)
        """
        super().__init__(**kwargs)
        self.max_chunks_per_source = max_chunks_per_source

    def process(self, chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        filtered_chunks = []
        source_counter = defaultdict(int)

        for chunk in chunks:
            source_title = chunk.metadata.title if chunk.metadata.title else "Unknown"

            if source_counter[source_title] < self.max_chunks_per_source:
                filtered_chunks.append(chunk)
                source_counter[source_title] += 1
            else:
                chunk.status = ChunkStatus.FILTERED_BY_THRESHOLD

        return filtered_chunks

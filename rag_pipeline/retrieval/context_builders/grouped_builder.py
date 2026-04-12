from ...core.models import Query, ScoredChunk, ContextBlock, ChunkStatus
from ..interfaces import BaseContextBuilder
from collections import defaultdict
from typing import List


class GroupedContextBuilder(BaseContextBuilder):
    def __init__(self, max_chars: int = 12000, **kwargs):
        super().__init__(**kwargs)
        self.max_chars = max_chars

    def build(self, query: Query, chunks: List[ScoredChunk]) -> List[ContextBlock]:
        if not chunks:
            return []

        grouped_chunks = defaultdict(list)
        for chunk in chunks:
            source_title = chunk.metadata.title or "Unknown Source"
            grouped_chunks[source_title].append(chunk)

        final_context_blocks = []
        current_total_chars = 0

        for title, source_chunks in grouped_chunks.items():
            # 1. Sort chunks by Vector Clock
            source_chunks.sort(key=lambda c: c.chunk_index or [])

            source_header = f"--- QUELLE: {title} ---\n"
            merged_content = source_header
            processed_original_chunks = []

            for chunk in source_chunks:
                addition = f"{chunk.page_content}\n[...]\n"

                # Check if this chunk still fits
                if current_total_chars + len(merged_content) + len(addition) > self.max_chars:
                    break

                merged_content += addition
                chunk.status = ChunkStatus.MERGED
                processed_original_chunks.append(chunk)

            # Only add the block if at least one chunk was included
            if processed_original_chunks:
                current_total_chars += len(merged_content)
                context_block = ContextBlock(page_content=merged_content.strip(),
                                             source_title=title,
                                             original_chunks=processed_original_chunks,
                                             max_score=max(c.score for c in processed_original_chunks))
                final_context_blocks.append(context_block)

            if current_total_chars >= self.max_chars:
                break

        # most relevant sources at the top
        final_context_blocks.sort(key=lambda b: b.max_score, reverse=True)

        return final_context_blocks

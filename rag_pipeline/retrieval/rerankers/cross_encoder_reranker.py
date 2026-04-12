from sentence_transformers import CrossEncoder
from ...core.models import Query, ScoredChunk
from ..interfaces import BaseReranker
from typing import List


class CrossEncoderReranker(BaseReranker):
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", max_length: int = 512, **kwargs):
        """
        Initializes the cross-encoder for reranking.

        :param model_name: Name of the HuggingFace cross-encoder model.
        :param max_length: Maximum token length for [Query + Chunk].
        """

        super().__init__(**kwargs)
        self.model = CrossEncoder(model_name, max_length=max_length)

    def rerank(self, query: Query, chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        """
        Re-evaluate the chunks by analyzing the question and chunk TOGETHER.
        """
        if not chunks:
            return []

        # 1. Pairs for cross encoder: [[Question, Chunk1], [Question, Chunk2], ...]
        sentence_pairs = [[query.text, chunk.page_content] for chunk in chunks]

        # 2. Model predicts new score values
        # List of floats (z.B. [5.2, -1.3, 8.4, ...])
        new_scores = self.model.predict(sentence_pairs)

        # 3. Join Chunks with new scores again
        for chunk, new_score in zip(chunks, new_scores):
            # Save old Score for traceability
            chunk.db_similarity_score = chunk.score
            chunk.score = float(new_score)

        return chunks

from ...core.models import Query, ScoredChunk
from ..interfaces import BaseRetriever
from typing import List, Dict


class HybridFusionRetriever(BaseRetriever):
    def __init__(self, retrievers: List[BaseRetriever], rrf_k: int = 60, top_k: int = 100, use_source_id: bool = False, **kwargs):
        """
        Combines multiple retrievers using Reciprocal Rank Fusion (RRF).

        :param retrievers: List of retriever instances (e.g., Vector + Keyword)
        :param rrf_k: Smoothing constant for RRF (standard is 60)
        :param top_k: Final number of chunks to return
        :param use_source_id: If True, fusion is done based on source_id (document level).
                              If False, fusion is done based on document_id (chunk level).
        """
        super().__init__(**kwargs)
        self.retrievers = retrievers
        self.rrf_k = rrf_k
        self.top_k = top_k
        self.use_source_id = use_source_id

    def retrieve(self, query: Query, top_k: int = 100) -> List[ScoredChunk]:
        """
        Executes all retrievers and fuses their results.
        """
        all_results: List[List[ScoredChunk]] = []
        
        # 1. Get results from all retrievers
        for retriever in self.retrievers:
            results = retriever.retrieve(query, top_k=top_k)
            all_results.append(results)

        if not all_results:
            return []

        # 2. Apply Reciprocal Rank Fusion (RRF)
        # map: target_id -> {chunk_object, rrf_score}
        fused_scores: Dict[str, float] = {}
        chunk_map: Dict[str, ScoredChunk] = {}

        for resultSet in all_results:
            # When using source_id, we only want to count the best rank per source_id in each result set
            seen_in_set = set()
            
            for rank, chunk in enumerate(resultSet, start=1):
                target_id = chunk.source_id if self.use_source_id else chunk.document_id
                
                if target_id in seen_in_set:
                    continue
                seen_in_set.add(target_id)
                
                if target_id not in fused_scores:
                    fused_scores[target_id] = 0.0
                    chunk_map[target_id] = chunk
                
                # RRF Formula: 1 / (k + rank)
                fused_scores[target_id] += 1.0 / (self.rrf_k + rank)

        # 3. Sort by fused score and convert back to ScoredChunk list
        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
        
        final_chunks = []
        for rank, target_id in enumerate(sorted_ids[:self.top_k], start=1):
            chunk = chunk_map[target_id]
            # Update score with RRF value
            chunk.score = fused_scores[target_id]
            chunk.rank = rank
            final_chunks.append(chunk)

        return final_chunks

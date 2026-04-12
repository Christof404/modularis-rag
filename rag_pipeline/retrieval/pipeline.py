from .interfaces import BaseRetriever, BaseFilter, BaseReranker, BaseContextBuilder, BaseFormatter, ContextBlock, ScoredChunk
from ..core.metrics import BasePerformanceTracker, NullTracker
from ..core.base_interfaces import BasePipeline, BaseEmbedder
from typing import List, Optional, Tuple, Any
from ..core.models import Query, Chunk


class RetrievalPipeline(BasePipeline):
    def __init__(self,
                 embedder: BaseEmbedder,
                 retriever: BaseRetriever,
                 context_builder: BaseContextBuilder,
                 formatter: BaseFormatter,
                 pre_filters: List[BaseFilter] = None,
                 post_filters: List[BaseFilter] = None,
                 reranker: Optional[BaseReranker] = None,
                 tracker: Optional[BasePerformanceTracker] = None):

        self.embedder = embedder
        self.reranker = reranker
        self.retriever = retriever
        self.formatter = formatter
        self.pre_filters = pre_filters or []
        self.post_filters = post_filters or []
        self.context_builder = context_builder
        self.tracker = tracker or NullTracker()

    @staticmethod
    def get_build_info() -> List[Tuple[str, Any]]:
        return [("embedder", BaseEmbedder),
                ("retriever", BaseRetriever),
                ("pre_filters", List[BaseFilter]),
                ("reranker", Optional[BaseReranker]),
                ("post_filters", List[BaseFilter]),
                ("context_builder", BaseContextBuilder),
                ("formatter", BaseFormatter)]

    def get_tracker(self) -> BasePerformanceTracker:
        return self.tracker

    def _run_filters(self, chunks, filter_list):
        for _filter in filter_list:
            if not chunks:
                break
            with self.tracker.measure(_filter.get_identifier().get("type"), _filter.name):
                chunks = _filter.process(chunks)

        return chunks

    def run(self, query_text: str, filters_dict: dict = None, evaluation_mode: bool=False) -> Tuple[str, List[ContextBlock], List[ScoredChunk]] | List[ScoredChunk]:
        """
        Executes the entire retrieval chain.

        :return: Finished prompt string for the LLM, list of final context blocks for the UI/logs, and the plain scored chunks.
        """
        with self.tracker.measure("RetrievalPipeline", "Total_Run"):
            # 1. init Query
            query = Query(text=query_text, filters=filters_dict or {})

            # 2. Query Embedding
            with self.tracker.measure(self.embedder.get_identifier().get("type"), self.embedder.name):
                query_doc = Chunk(page_content=query.text, source_id="")  # source id is not required for user id
                embedded_docs = self.embedder.embed([query_doc])
                query.embedding = embedded_docs[0].embedding

            # 3. DB Retrieval (Postgres Vector Search)
            with self.tracker.measure(self.retriever.get_identifier().get("type"), self.retriever.name):
                chunks = self.retriever.retrieve(query)

            # 4. Pre-Filtering (Filters e.g. Threshold, Diversity, Top K)
            chunks = self._run_filters(chunks, self.pre_filters)

            # 5. Reranking (Cross-Encoder)
            if self.reranker and chunks:
                with self.tracker.measure(self.reranker.get_identifier().get("type"), self.reranker.name):
                    chunks = self.reranker.rerank(query, chunks)

            # 6. Post-Filtering (Filters e.g. Threshold, Diversity, Top K)
            chunks = self._run_filters(chunks, self.post_filters)

            if evaluation_mode:
                # for evaluation no context building and formatting is required
                return chunks

            # 6. Context Building (Merge by Vektor-Uhr and source)
            with self.tracker.measure(self.context_builder.get_identifier().get("type"), self.context_builder.name):
                context_blocks = self.context_builder.build(query, chunks)

            # 7. Formatting
            with self.tracker.measure(self.formatter.get_identifier().get("type"), self.formatter.name):
                final_response = self.formatter.format(query, context_blocks)

            return final_response, context_blocks, chunks

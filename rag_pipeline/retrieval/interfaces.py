from ..core.models import Query, ScoredChunk, ContextBlock
from ..core.base_interfaces import PipelineComponent
from abc import abstractmethod
from typing import List


# Step 1: QueryEmbedder -> Implemented with BaseEmbedder core/base_interfaces

class BaseRetriever(PipelineComponent):
    """
    Step 2: DB Reader.
    Retrieves the most relevant chunks from the vector database (e.g., via cosine similarity).
    """
    @abstractmethod
    def retrieve(self, query: Query, top_k: int = 100) -> List[ScoredChunk]:
        """
        :param query: The embedded search query
        :param top_k: Maximum number of chunks to be retrieved from the DB
        :return: List of evaluated ScoredChunks
        """
        pass

class BaseFilter(PipelineComponent):
    """
    Step 3: Candidate Filter.
    Sorts chunks after database retrieval (e.g., thresholds, source balancing).
    """
    @abstractmethod
    def process(self, chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        """
        :return: Cleaned list of ScoredChunks
        """
        pass

class BaseReranker(PipelineComponent):
    """
    Step 4: Reranker.
    Re-evaluate the filtered chunks (e.g., with a cross-encoder) and sort them.
    """
    @abstractmethod
    def rerank(self, query: Query, chunks: List[ScoredChunk]) -> List[ScoredChunk]:
        """
        :param chunks: filtered chunks from postfilter
        :param query: The original search query
        :return: Newly sorted and rated list from ScoredChunks
        """
        pass

class BaseContextBuilder(PipelineComponent):
    """
    Step 5: Context Builder.
    Combines adjacent chunks (merging) or applies token limits.
    """
    @abstractmethod
    def build(self, query: Query, chunks: List[ScoredChunk]) -> List[ContextBlock]:
        """
        :return: The final list of chunks sent to the LLM
        """
        pass

class BaseFormatter(PipelineComponent):
    """
    Step 6: Answer Prompt Builder.
    Converts the final chunks into the string that the LLM receives as a tool response.
    """
    @abstractmethod
    def format(self, query: Query, context_blocks: List[ContextBlock]) -> str:
        """
        :return:  The fully formatted context string (including source references)
        """
        pass

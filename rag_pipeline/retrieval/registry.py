from .response_formatter.default_response_formatter import DefaultResponseFormatter
from .retrievers.postgres_keyword_retriever import PostgresKeywordRetriever
from .retrievers.postgres_bm25_retriever import PostgresBM25Retriever
from .retrievers.hybrid_fusion_retriever import HybridFusionRetriever
from .context_builders.grouped_builder import GroupedContextBuilder
from .rerankers.cross_encoder_reranker import CrossEncoderReranker
from .retrievers.postgres_retriever import PostgresVectorRetriever
from .filters.diversity_filter import SourceDiversityFilter
from .filters.threshold_filter import ScoreThresholdFilter
from ..embedders.ollama_embedder import OllamaEmbedder
from .filters.top_k_filter import TopKFilter


# Central registry for all pipeline components
REGISTRY = {
    "embedder": {
        "OllamaEmbedder": OllamaEmbedder
    },
    "retriever": {
        "PostgresVectorRetriever": PostgresVectorRetriever,
        "PostgresKeywordRetriever": PostgresKeywordRetriever,
        "PostgresBM25Retriever": PostgresBM25Retriever,
        "HybridFusionRetriever": HybridFusionRetriever
    },
    "filter": {
        "SourceDiversityFilter": SourceDiversityFilter,
        "ScoreThresholdFilter": ScoreThresholdFilter,
        "TopKFilter": TopKFilter
    },
    "reranker": {
        "CrossEncoderReranker": CrossEncoderReranker
    },
    "contextbuilder": {
        "GroupedContextBuilder": GroupedContextBuilder
    },
    "formatter": {
        "DefaultResponseFormatter": DefaultResponseFormatter
    }
}

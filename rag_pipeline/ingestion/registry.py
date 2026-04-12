from .chunkers.experimental_llm_chunkers.hypothetical_question_chunker import HypotheticalQuestionChunker
from .chunkers.experimental_llm_chunkers.experimental_raptor_chunker import ExperimentalRaptorChunker
from .chunkers.markdown_header_text_splitter_chunker import MarkdownHeaderTextSplitterChunker
from .chunkers.experimental_llm_chunkers.propositional_chunker import PropositionalChunker
from .chunkers.experimental_llm_chunkers.contextual_chunker import ContextualChunker
from .extractors.markdown_code_block_extractor import MarkdownCodeBlockExtractor
from .filters.markdown_fragment_link_filter import MarkdownFragmentLinkFilter
from .chunkers.recursive_character_chunker import RecursiveCharacterChunker
from .converters.html_to_markdown_converter import HTMLToMarkdownConverter
from .chunkers.hugging_face_token_chunker import HuggingFaceTokenChunker
from .converters.url_to_markdown_converter import UrlToMarkdownConverter
from .extractors.markdown_table_extractor import MarkdownTableExtractor
from .filters.wikipedia_citation_filter import WikipediaCitationFilter
from .sources.GoogleNQ.fetch_google_nq_dataset import GoogleNQSource
from .filters.markdown_section_filter import MarkdownSectionFilter
from .chunkers.semantic_text_chunker import SemanticTextChunker
from .filters.universal_html_filter import UniversalHtmlFilter
from .filters.markdown_image_filter import MarkdownImageFilter
from .filters.markdown_link_filter import MarkdownLinkFilter
from .filters.regex_replace_filter import RegexReplaceFilter
from .chunkers.window_chunker import SentenceWindowChunker
from .filters.length_guard_filter import LengthGuardFilter
from .filters.text_cleanup_filter import TextCleanupFilter
from .db_writers.postgres_db_writer import PostgresWriter
from .filters.token_limit_filter import TokenLimitFilter
from .filters.remove_tags_filter import RemoveTagsFilter
from .converters.bypass_converter import ByPassConverter
from .sources.BEIR.fetch_beir_dataset import BEIRSource
from ..core.metrics import PipelineTracker, NullTracker
from ..embedders.ollama_embedder import OllamaEmbedder
from .extractors.link_extractor import LinkExtractor
from .sources.WebUrl.url_souce import UrlSource


# Central registry for all pipeline components
REGISTRY = {
    "source": {
        "UrlSource": UrlSource,
        "BEIRSource": BEIRSource,
        "GoogleNQSource": GoogleNQSource
    },
    "converter": {
        "UrlToMarkdownConverter": UrlToMarkdownConverter,
        "HTMLToMarkdownConverter": HTMLToMarkdownConverter,
        "ByPassConverter": ByPassConverter
    },
    "filter": {
        "LengthGuardFilter": LengthGuardFilter,
        "MarkdownImageFilter": MarkdownImageFilter,
        "MarkdownLinkFilter": MarkdownLinkFilter,
        "MarkdownSectionFilter": MarkdownSectionFilter,
        "RegexReplaceFilter": RegexReplaceFilter,
        "TextCleanupFilter": TextCleanupFilter,
        "WikipediaCitationFilter": WikipediaCitationFilter,
        "MarkdownFragmentLinkFilter": MarkdownFragmentLinkFilter,
        "UniversalHtmlFilter": UniversalHtmlFilter,
        "TokenLimitFilter": TokenLimitFilter,
        "RemoveTagsFilter": RemoveTagsFilter
    },
    "chunker": {
        "ContextualChunker": ContextualChunker,
        "ExperimentalRaptorChunker": ExperimentalRaptorChunker,
        "HypotheticalQuestionChunker": HypotheticalQuestionChunker,
        "MarkdownHeaderTextSplitterChunker": MarkdownHeaderTextSplitterChunker,
        "PropositionalChunker": PropositionalChunker,
        "RecursiveCharacterChunker": RecursiveCharacterChunker,
        "SemanticTextChunker": SemanticTextChunker,
        "SentenceWindowChunker": SentenceWindowChunker,
        "HuggingFaceTokenChunker": HuggingFaceTokenChunker

    },
    "extractor": {
        "MarkdownTableExtractor": MarkdownTableExtractor,
        "LinkExtractor": LinkExtractor,
        "MarkdownCodeBlockExtractor": MarkdownCodeBlockExtractor
    },
    "embedder": {
        "OllamaEmbedder": OllamaEmbedder
    },
    "writers": {
        "PostgresWriter": PostgresWriter
    },
    "performancetracker": {
        "PipelineTracker": PipelineTracker,
        "NullTracker": NullTracker
    },
    "databasewriter": {
        "PostgresWriter": PostgresWriter
    }
}

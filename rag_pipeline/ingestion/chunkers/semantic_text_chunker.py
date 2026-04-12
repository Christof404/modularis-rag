from langchain_experimental.text_splitter import SemanticChunker
from transformers import AutoTokenizer, PreTrainedTokenizerBase
from ..interfaces import BaseChunker, BaseFilter, BaseExtractor
from ...core.models import Document, ContentType, Chunk
from typing import List, Optional, Literal, Union, cast
from langchain_core.embeddings import Embeddings
from ...core.base_interfaces import BaseEmbedder
import numpy as np


class _LangChainEmbedderAdapter(Embeddings):
    """
    Adapter for LangChain, as LangChain expects the functions embed_documents and embed_query.
    Handles texts longer than max_tokens by splitting them and averaging their embeddings.
    """

    def __init__(self, base_embedder: BaseEmbedder, tokenizer_model_name: str):
        self.base_embedder = base_embedder
        self.max_tokens = self.base_embedder.get_model().max_tokens
        self.tokenizer = cast(PreTrainedTokenizerBase, AutoTokenizer.from_pretrained(tokenizer_model_name, trust_remote_code=True))

        self.prefix_tokens_len = len(self.tokenizer.encode(f"{self.base_embedder.get_prefix()} ", add_special_tokens=False))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # 1. Prepare tasks: for each text, decide if it needs splitting
        text_tasks: List[List[str]] = []
        all_sub_chunks_to_embed: List[Chunk] = []

        for text in texts:
            tokens = self.tokenizer.encode(text, add_special_tokens=False)
            total_token_length = self.prefix_tokens_len + len(tokens)
            available_capacity = self.max_tokens - self.prefix_tokens_len

            if total_token_length <= self.max_tokens:
                text_tasks.append([text])
                all_sub_chunks_to_embed.append(Chunk(page_content=text, source_id=""))
            else:
                sub_texts = []
                for i in range(0, len(tokens), available_capacity):
                    sub_tokens = tokens[i : i + available_capacity]
                    sub_text = self.tokenizer.decode(sub_tokens, skip_special_tokens=True)
                    sub_texts.append(sub_text)
                    all_sub_chunks_to_embed.append(Chunk(page_content=sub_text, source_id=""))
                text_tasks.append(sub_texts)

        # 2. Batch embed all collected sub-chunks
        embedded_results = self.base_embedder.embed(all_sub_chunks_to_embed)
        embedding_map = {res.page_content: res.embedding for res in embedded_results}

        # 3. Reconstruct original structure and apply mean pooling where necessary
        final_embeddings: List[List[float]] = []
        for sub_texts in text_tasks:
            # Collect embeddings for this specific text (could be one or many)
            current_embeddings = [embedding_map.get(st) for st in sub_texts if embedding_map.get(st) is not None]

            if not current_embeddings:
                # Fallback: return zero vector if embedding failed
                dim = self.base_embedder.get_model().model_dimension
                final_embeddings.append([0.0] * dim)
            elif len(current_embeddings) == 1:
                # Standard case: just one embedding
                final_embeddings.append(current_embeddings[0])
            else:
                # Multipart case: calculate mean
                mean_vec = np.mean(current_embeddings, axis=0).tolist()
                final_embeddings.append(mean_vec)

        return final_embeddings

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class SemanticTextChunker(BaseChunker):
    def __init__(self,
                 embedder: BaseEmbedder,
                 tokenizer_model_name: str,
                 breakpoint_threshold_type: Literal["percentile", "standard_deviation", "interquartile", "gradient"] = "percentile",
                 breakpoint_threshold_amount: Optional[float] = None,
                 sentence_split_regex: str = r"(?<=[.?!])\s+",
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):

        super().__init__(filters, extractors, **kwargs)

        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]
        self.breakpoint_threshold_type = breakpoint_threshold_type

        # use adapter
        langchain_compatible_embedder = _LangChainEmbedderAdapter(embedder, tokenizer_model_name)
        self.chunker = SemanticChunker(langchain_compatible_embedder,
                                       breakpoint_threshold_type=breakpoint_threshold_type,
                                       breakpoint_threshold_amount=breakpoint_threshold_amount,
                                       sentence_split_regex=sentence_split_regex)

    def chunk(self, doc: Union[Document, Chunk]) -> List[Chunk]:
        """
        Takes a document and returns a list of chunked documents.
        Copies the associated metadata from the original document.
        """
        # only chunks allowed docs
        current_type = getattr(doc.metadata, 'content_type', ContentType.TEXT)
        if current_type not in self.target_content_types:
            return [doc]

        extractor_chunks, doc = self._apply_extractors(doc)
        if not doc:
            return self._apply_filters(extractor_chunks)

        content = doc.page_content
        splits = self.chunker.split_text(content)
        chunk_index_list = self._get_chunk_index_list(doc)

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description=f"semantic_threshold: {self.breakpoint_threshold_type}").copy(content_type=ContentType.CHUNK)

        raw_chunks = [Chunk(page_content=split_text,
                            chunk_index=chunk_index_list + [index],
                            metadata=new_metadata,
                            source_id=doc.source_id) for index, split_text in enumerate(splits)]
        raw_chunks = extractor_chunks + raw_chunks

        return self._apply_filters(raw_chunks)

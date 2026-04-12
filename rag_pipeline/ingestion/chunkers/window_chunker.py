# Sentence Window Retrieval / Small-to-Big Retrieval
from ..interfaces import BaseChunker, BaseFilter, BaseExtractor
from ...core.models import Document, ContentType, Chunk
from typing import List, Union
import re


class SentenceWindowChunker(BaseChunker):
    def __init__(self,
                 window_size: int = 2,  # 2 Sentences before, 2 sentences after
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):

        super().__init__(filters, extractors, **kwargs)

        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]
        self.window_size = window_size

    def chunk(self, doc: Union[Document, Chunk]) -> List[Chunk]:
        # only chunks allowed docs
        current_type = getattr(doc.metadata, 'content_type', ContentType.TEXT)
        if current_type not in self.target_content_types:
            return [doc]

        extractor_chunks, doc = self._apply_extractors(doc)
        if not doc:
            return self._apply_filters(extractor_chunks)
        
        chunk_index_list = self._get_chunk_index_list(doc)
        content = doc.page_content

        # 1. Split text into sentences via regex
        # Splits on ., !, ? + space; lookbehind (?<=...) keeps punctuation
        raw_sentences = re.split(r'(?<=[.?!])\s+', content)

        # Remove empty strings and strip whitespace
        sentences = [s.strip() for s in raw_sentences if s.strip()]
        chunked_documents = []

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description=f"window_size: {self.window_size}").copy(content_type=ContentType.CHUNK)

        # 2. move sliding window over sentences
        for i, sentence in enumerate(sentences):
            # Compute window index bounds to prevent IndexError at text edges
            start_idx = max(0, i - self.window_size)
            end_idx = min(len(sentences), i + self.window_size + 1)

            window_sentences = sentences[start_idx:end_idx]
            window_text = " ".join(window_sentences)

            chunk_doc = Chunk(page_content=window_text,
                              embed_content=sentence,
                              chunk_index=chunk_index_list + [i],
                              metadata=new_metadata,
                              source_id=doc.source_id)

            chunked_documents.append(chunk_doc)

        chunked_documents = extractor_chunks + chunked_documents
        return self._apply_filters(chunked_documents)
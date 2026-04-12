from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..interfaces import BaseChunker, BaseFilter, BaseExtractor
from ...core.models import Document, ContentType, Chunk
from typing import List, Optional, Callable, Union


class RecursiveCharacterChunker(BaseChunker):
    def __init__(self,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 separators: Optional[List[str]] = None,
                 length_function: Callable[[str], int] = len,
                 is_separator_regex: bool = False,
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):

        super().__init__(filters, extractors, **kwargs)

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]

        self.chunker = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                                      chunk_overlap=chunk_overlap,
                                                      separators=separators,
                                                      length_function=length_function,
                                                      is_separator_regex=is_separator_regex)

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
                                                  description=f"chunk_size: {self.chunk_size} overlap:{self.chunk_overlap}").copy(content_type=ContentType.CHUNK)

        raw_chunks = [Chunk(page_content=split_text,
                            chunk_index=chunk_index_list + [index],
                            metadata=new_metadata,
                            source_id=doc.source_id) for index, split_text in enumerate(splits)]
        raw_chunks = extractor_chunks + raw_chunks

        return self._apply_filters(raw_chunks)

from langchain_text_splitters import MarkdownHeaderTextSplitter
from ..interfaces import BaseChunker, BaseFilter, BaseExtractor
from ...core.models import Document, ContentType, Chunk
from typing import List, Union


class MarkdownHeaderTextSplitterChunker(BaseChunker):
    def __init__(self,
                 headers_to_split_on: List[tuple] = None,
                 strip_headers: bool = False,
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):

        super().__init__(filters, extractors, **kwargs)
        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]

        # Default headers if none provided
        if headers_to_split_on is None:
            headers_to_split_on = [("#", "Header 1"),
                                   ("##", "Header 2"),
                                   ("###", "Header 3"),
                                   ("####", "Header 4")]

        self.chunker = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,
                                                  return_each_line=False,
                                                  strip_headers=strip_headers)

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

        # Convert splits to Document objects with copied metadata
        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name).copy(content_type=ContentType.CHUNK)

        raw_chunks = [Chunk(page_content=split.page_content,
                            chunk_index=chunk_index_list + [index],
                            metadata=new_metadata.copy(header=split.metadata),
                            source_id=doc.source_id) for index, split in enumerate(splits)]

        raw_chunks = extractor_chunks + raw_chunks
        return self._apply_filters(raw_chunks)

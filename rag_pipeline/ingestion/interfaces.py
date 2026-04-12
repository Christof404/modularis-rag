from ..core.models import Document, Chunk, EmbeddedChunk, Metadata
from typing import Iterator, List, Optional, Literal, Tuple, Union
from ..core.base_interfaces import PipelineComponent
from abc import abstractmethod

class BaseSource(PipelineComponent):
    """
    Load Data like raw strings or urls
    """

    @abstractmethod
    def load(self) -> Iterator[Document]:
        """
        :return Iterator[Document] to save memory
        """
        pass

class BaseConverter(PipelineComponent):
    """
    Converts raw Data (PDF, Excel, URL) in clean text or markdown.
    """

    @abstractmethod
    def convert(self, doc: Document) -> Optional[Document]:
        """
         Extracts specialized structures from the document (e.g., tables, code blocks).

        :return: A tuple containing:
                 1. A list of extracted chunks (each as a Document).
                 2. The remaining document with the extracted structures removed.
        """
        pass

class BaseFilter(PipelineComponent):
    """
    Clean up or sort content based on various factors such as length or structure.
    """

    def __init__(self, apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        super().__init__(**kwargs)
        self.apply_to = apply_to

    def process(self, doc: Union[Document, Chunk]) -> Optional[Union[Document, Chunk]]:
        """
        Clean up document or mark as junk

        :return Document or None if the Document should not be processed
        """
        page_content = self.process_text(doc.page_content) if self.apply_to in ("page_content", "both") else doc.page_content
        embed_content = None if not doc.embed_content else self.process_text(doc.embed_content) if self.apply_to in ("embed_content", "both") else doc.embed_content

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description=self.metadata_description).copy()

        # only check page content -> Embedder use always page_content if embed_content is not available
        if isinstance(doc, Chunk):
            return Chunk(page_content=page_content,
                          embed_content=embed_content,
                          chunk_index=doc.chunk_index,
                          metadata=new_metadata,
                          source_id=doc.source_id) if page_content else None

        return Document(page_content=page_content,
                        embed_content=embed_content,
                        metadata=new_metadata,
                        source_id=doc.source_id) if page_content else None

    @abstractmethod
    def process_text(self, text_content: str) -> Optional[str]:
        pass

    @property
    def metadata_description(self) -> Optional[str]:
        # Default = PipelineStep.description default (which is None)
        return None


class BaseExtractor(PipelineComponent):
    """
    Searches for specific structures (tables, code blocks), extracts them
    as finished chunks and removes them from the main document.
    """

    def __init__(self, filters: List[BaseFilter] = None, **kwargs):
        super().__init__(**kwargs)
        self.filters = filters or []

    @abstractmethod
    def extract(self, doc: Union[Document, Chunk]) -> Tuple[List[Chunk], Optional[Union[Document, Chunk]]]:
        """
         Extracts specialized structures from the document (e.g., tables, code blocks).

        :return: A tuple containing:
                 1. A list of extracted chunks (each as a Document).
                 2. The remaining document with the extracted structures removed.
        """
        pass

    @staticmethod
    def _create_doc(doc, remaining_text: str, new_metadata: Metadata) -> Union[Document, Chunk]:
        if isinstance(doc, Chunk):
            return Chunk(page_content=remaining_text,
                         embed_content=doc.embed_content,
                         chunk_index=doc.chunk_index,
                         metadata=new_metadata,
                         source_id=doc.source_id)
        else:
            return Document(page_content=remaining_text,
                            embed_content=doc.embed_content,
                            metadata=new_metadata,
                            source_id=doc.source_id)

    def _apply_filters(self, chunks: List[Union[Document, Chunk]]) -> List[Union[Document, Chunk]]:
        if not self.filters:
            return chunks

        filtered_chunks = []
        for chunk_doc in chunks:
            for _filter in self.filters:
                chunk_doc = _filter.process(chunk_doc)
                if not chunk_doc:
                    break

            if chunk_doc:
                filtered_chunks.append(chunk_doc)

        return filtered_chunks

class BaseChunker(PipelineComponent):
    """
    Responsible for breaking down large documents into smaller, semantic or fixed sections.
    """

    def __init__(self,
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 **kwargs):

        super().__init__(**kwargs)
        self.filters = filters or []
        self.extractors = extractors or []

    @abstractmethod
    def chunk(self, doc: Union[Document, Chunk]) -> List[Chunk]:
        """
        Takes a document and return a list of chunked documents
        Copies the associated metadata from each document

        :return List[Document]
        """
        pass

    def _apply_extractors(self, doc: Union[Document, Chunk]) -> Tuple[List[Chunk], Optional[Document]]:
        """
        Passes the document through all extractors.
        Gathers the finished chunks and forwards the shortened text.
        """

        if not self.extractors:
            return [], doc

        all_extracted_chunks = []
        current_doc = doc

        for extractor in self.extractors:
            if current_doc is None:
                break

            extracted_chunks, current_doc = extractor.extract(current_doc)
            all_extracted_chunks.extend(extracted_chunks)

        return all_extracted_chunks, current_doc

    def _apply_filters(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Applies all registered filters to a list of chunks.
        Sorts out chunks that are rejected (None) by a filter.
        """
        if not self.filters:
            return chunks

        filtered_chunks = []
        for chunk_doc in chunks:
            for _filter in self.filters:
                chunk_doc = _filter.process(chunk_doc)
                if not chunk_doc:
                    break

            # Only add chunked documents if they pass all filters
            if chunk_doc:
                filtered_chunks.append(chunk_doc)

        return filtered_chunks

    @staticmethod
    def _get_chunk_index_list(doc: Union[Document, Chunk]) -> List[int]:
        if isinstance(doc, Chunk):
            return doc.chunk_index
        else:
            return []


class BaseDatabaseWriter(PipelineComponent):
    """
    Responsible for storing the finished chunks in a database.
    """
    @abstractmethod
    def write(self, chunks: List[EmbeddedChunk]) -> None:
        """
        Takes a list of finished (vectorized) chunks and writes them to the database.
        """
        pass

    @abstractmethod
    def is_processed(self, source_id: str) -> bool:
        """
        Checks if a document with the given source_id (hash or unique url) has already been processed.
        """
        pass
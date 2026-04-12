from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..interfaces import BaseChunker, BaseFilter, BaseExtractor
from transformers import AutoTokenizer, PreTrainedTokenizerBase
from ...core.models import Document, ContentType, Chunk
from typing import List, Union
from typing import cast
import logging

# Suppress tokenization warnings about sequence length
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)


class HuggingFaceTokenChunker(BaseChunker):
    def __init__(self,
                 model_name: str,
                 chunk_size: int = 500,
                 chunk_overlap: int = 50,
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):

        super().__init__(filters=filters, extractors=extractors, **kwargs)

        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]
        self.chunk_overlap = chunk_overlap
        self.chunk_size = chunk_size
        self.model_name = model_name

        self.tokenizer = cast(PreTrainedTokenizerBase, AutoTokenizer.from_pretrained(model_name, trust_remote_code=True))  # cast because of type issues in AutoTokenizer
        self.chunker = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(self.tokenizer,
                                                                                 chunk_size=chunk_size,
                                                                                 chunk_overlap=chunk_overlap,
                                                                                 separators=["\n\n", "\n", " ", ""])

    def chunk(self, doc: Union[Document, Chunk]) -> List[Chunk]:
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
                                                  description=f"token_size: {self.chunk_size}, "
                                                              f"overlap: {self.chunk_overlap}, "
                                                              f"model: {self.model_name}").copy(content_type=ContentType.CHUNK)

        raw_chunks = [Chunk(page_content=split_text,
                            chunk_index=chunk_index_list + [index],
                            metadata=new_metadata,
                            source_id=doc.source_id) for index, split_text in enumerate(splits)]

        raw_chunks = extractor_chunks + raw_chunks
        return self._apply_filters(raw_chunks)

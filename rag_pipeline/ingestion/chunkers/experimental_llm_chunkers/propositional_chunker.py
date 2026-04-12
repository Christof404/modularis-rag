# innovation from paper: Dense X Retrieval: What Retrieval Granularity Should We Use?
from ...interfaces import BaseChunker, BaseFilter, BaseExtractor
from ....core.models import Document, ContentType, Chunk
from pydantic import BaseModel
from typing import List, Union
import ollama
import json


class PropositionalChunks(BaseModel):
  propositional_chunks: list[str]


class PropositionalChunker(BaseChunker):
    def __init__(self,
                 llm_model_name: str = 'gpt-oss:20b',
                 llm_prompt: str = None,
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):

        super().__init__(filters, extractors, **kwargs)

        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]
        self.llm_model_name = llm_model_name
        self.client = ollama.Client()

        # llm prompt from Dense X Retrieval paper, only translated to german
        self.llm_prompt = llm_prompt or (f'Decompose the "Content" into clear and simple propositions, ensuring that they can be understood out of context.\n\n'
                                         '1. Split compound sentences into simple sentences. Maintain the original phrasing from the input whenever possible.\n'
                                         '2. For any named entity that is accompanied by additional descriptive information, separate this information into its own distinct proposition.\n'
                                         '3. Decontextualize each proposition by adding necessary modifiers to nouns or entire sentences and replacing pronouns (e.g., "it", "he", "she", "they", "this", "that") with the full names of the entities they refer to.\n'
                                         f'4. Present the results in JSON format according to this schema: {json.dumps(PropositionalChunks.model_json_schema())}')


    def chunk(self, doc: Union[Document, Chunk]) -> List[Chunk]:
        # only chunks allowed docs
        current_type = getattr(doc.metadata, 'content_type', ContentType.TEXT)
        if current_type not in self.target_content_types:
            return [doc]

        extractor_chunks, doc = self._apply_extractors(doc)
        if not doc:
            return self._apply_filters(extractor_chunks)

        content = doc.page_content
        splits = self._chunk_with_llm(content)
        chunk_index_list = self._get_chunk_index_list(doc)

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description=f"llm_model {self.llm_model_name}").copy(content_type=ContentType.CHUNK)

        raw_chunks = [Chunk(page_content=split_text,
                            chunk_index=chunk_index_list + [index],
                            metadata=new_metadata,
                            source_id=doc.source_id) for index, split_text in enumerate(splits)]
        raw_chunks = extractor_chunks + raw_chunks

        return self._apply_filters(raw_chunks)


    def _chunk_with_llm(self, paragraph) -> List[str]:
        try:
            response = self.client.chat(messages=[{'role': 'system', 'content': self.llm_prompt},
                                                  {'role': 'user', 'content': f'Text:\n{paragraph}'}],
                                        model=self.llm_model_name,
                                        options={'temperature': 0}, # try to force json output
                                        format=PropositionalChunks.model_json_schema())

            result = PropositionalChunks.model_validate_json(response.message.content)
            return result.propositional_chunks
        except Exception as e:
            print(f"[Warning]: LLM chunking failed for paragraph. Remove chunk: {e}")
            return []

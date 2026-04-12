# Anthropic
from ...interfaces import BaseChunker, BaseFilter, BaseExtractor
from ....core.models import Document, ContentType, Chunk
from pydantic import BaseModel
from typing import List, Union
import ollama
import json


class ContextChunks(BaseModel):
  context: str

class ContextualChunker(BaseChunker):
    def __init__(self,
                 base_chunker: BaseChunker,
                 llm_model_name: str = 'gpt-oss:20b',
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):

        super().__init__(filters=filters, extractors=extractors, **kwargs)

        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]
        self.llm_model_name = llm_model_name
        self.base_chunker = base_chunker
        self.client = ollama.Client()


    def chunk(self, doc: Union[Document, Chunk]) -> List[Chunk]:
        # only chunks allowed docs
        current_type = getattr(doc.metadata, 'content_type', ContentType.TEXT)
        if current_type not in self.target_content_types:
            return [doc]

        raw_chunks, doc = self._apply_extractors(doc)
        if not doc:
            return self._apply_filters(raw_chunks)
        content = doc.page_content

        # generate chunks with provided Base Chunker
        splits = self.base_chunker.chunk(doc)
        chunk_index_list = self._get_chunk_index_list(doc)

        for index, chunk in enumerate(splits):
            chunk_text = chunk.page_content
            prompt = self._generate_llm_prompt(content, chunk_text)
            context = self._chunk_with_llm(prompt)

            new_chunk_text = f"{context}\n{chunk_text}" if context else chunk_text
            new_metadata = chunk.metadata.pipeline_step(component_type=self._type,
                                                        component_name=self.name,
                                                        description=f"base_chunker: {self.base_chunker.name}, llm_model: {self.llm_model_name}").copy(content_type=ContentType.CHUNK)

            raw_chunks.append(Chunk(page_content=new_chunk_text,
                                    chunk_index=chunk_index_list + [index],
                                    metadata=new_metadata,
                                    source_id=doc.source_id))

        return self._apply_filters(raw_chunks)


    def _chunk_with_llm(self, prompt) -> str:
        try:
            response = self.client.chat(messages=[{'role': 'user', 'content': prompt}],
                                        model=self.llm_model_name,
                                        options={'temperature': 0}, # try to force json output
                                        format=ContextChunks.model_json_schema())

            result = ContextChunks.model_validate_json(response.message.content)
            return result.context
        except Exception as e:
            print(f"[Warning]: LLM chunking failed for paragraph. Remove chunk: {e}")
            return ''


    @staticmethod
    def _generate_llm_prompt(whole_text, chunk_text):
        # exact prompt from Anthropic
        llm_prompt = (f"<document>{whole_text}</document>\n\n"
                      f"Hier ist der Abschnitt, den wir im gesamten Dokument platzieren möchten.\n"
                      f"<chunk>\n{chunk_text}\n</chunk>\n\n"
                      f"Bitte geben Sie einen kurzen, prägnanten Kontext (2-3 Sätze) an, um diesen Abschnitt innerhalb des Gesamtdokuments einzuordnen und die Suche nach diesem Abschnitt zu verbessern. Antworten Sie nur mit dem prägnanten Kontext und nichts anderem in folgendem JSON Format: {json.dumps(ContextChunks.model_json_schema())}.")

        return llm_prompt


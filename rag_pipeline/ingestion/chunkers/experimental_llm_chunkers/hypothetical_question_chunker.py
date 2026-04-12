# Document Expansion by Query Prediction" (Doc2Query) von Nogueira et al. (2019), DocT5Query
from ....core.models import Document, ContentType, Chunk
from ...interfaces import BaseChunker, BaseFilter
from pydantic import BaseModel
from typing import List, Union
import ollama
import json

class QAPair(BaseModel):
    question: str
    answer: str

class QuestionAnswer(BaseModel):
    qa_pairs: List[QAPair]

class HypotheticalQuestionChunker(BaseChunker):
    def __init__(self,
                 llm_model_name: str = 'gpt-oss:20b',
                 filters: List[BaseFilter] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):

        super().__init__(filters, **kwargs)

        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]
        self.llm_model_name = llm_model_name
        self.client = ollama.Client()

    def chunk(self, doc: Union[Document, Chunk]) -> List[Chunk]:
        # only chunks allowed docs
        current_type = getattr(doc.metadata, 'content_type', ContentType.TEXT)
        if current_type not in self.target_content_types:
            return [doc]

        content = doc.page_content
        qa_result = self._generate_questions_answers(content)
        chunk_index_list = self._get_chunk_index_list(doc)

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description=f"llm_model {self.llm_model_name}").copy(content_type=ContentType.CHUNK)
        raw_chunks = []
        if qa_result and qa_result.qa_pairs:
            for index, pair in enumerate(qa_result.qa_pairs):
                raw_chunks.append(Chunk(page_content=pair.answer,
                                        embed_content=pair.question,
                                        chunk_index=chunk_index_list + [index],
                                        metadata=new_metadata,
                                        source_id=doc.source_id))

        return self._apply_filters(raw_chunks)

    def _generate_questions_answers(self, paragraph):
        llm_prompt = (f"Du bist ein Experte für Suchmaschinenoptimierung und Information Retrieval.\n"
                      f"Deine Aufgabe ist es, hypothetische Suchanfragen (Fragen) zu formulieren, "
                      f"die durch den folgenden Text präzise beantwortet werden.\n\n"
                      f"<text>\n{paragraph}\n</text>\n\n"
                      f"Regeln:\n"
                      f"1. Die Fragen müssen ausschließlich mit diesem Text beantwortbar sein.\n"
                      f"2. Formuliere wie ein echter Nutzer (z.B. 'Wann wurde Rom gegründet?').\n"
                      f"3. Generiere so viele Fragen und Antworten, bis die gesamte Information des Textes "
                      f"vollständig durch die Antworten abgedeckt ist. Eine Frage soll zudem nach einer "
                      f"Zusammenfassung des Textes fragen.\n\n"
                      f"Antworte strikt in folgendem JSON Format: {json.dumps(QuestionAnswer.model_json_schema())}")

        try:
            response = self.client.chat(messages=[{'role': 'user', 'content': llm_prompt}],
                                        model=self.llm_model_name,
                                        options={'temperature': 0}, # try to force json output
                                        format=QuestionAnswer.model_json_schema())

            result = QuestionAnswer.model_validate_json(response.message.content)
            return result

        except Exception as e:
            print(f"[Warning]: LLM chunking failed for paragraph. Remove chunk: {e}")
            return None

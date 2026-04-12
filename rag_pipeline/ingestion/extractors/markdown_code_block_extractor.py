from ...core.models import Document, ContentType, Chunk
from ..interfaces import BaseExtractor, BaseFilter
from typing import List, Tuple, Optional, Union
import re


class MarkdownCodeBlockExtractor(BaseExtractor):
    def __init__(self, filters: List[BaseFilter] = None):
        super().__init__(filters=filters)

    def extract(self, doc: Union[Document, Chunk]) -> Tuple[List[Chunk], Optional[Union[Document, Chunk]]]:
        text = doc.page_content

        code_pattern = re.compile(r'```([^\n]*)\n(.*?)```', re.DOTALL)
        extracted_chunks = []

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description="Extract code blocks and save them as new document").copy(content_type=ContentType.CODE)
        for match in code_pattern.finditer(text):
            language = match.group(1).strip()
            code_content = match.group(2).strip()

            if language:
                chunk_content = f"Language: {language}\nCode:\n{code_content}"
            else:
                chunk_content = f"Code:\n{code_content}"

            # no chunk index required for extracted text
            extracted_chunks.append(Chunk(page_content=chunk_content,
                                          metadata=new_metadata,
                                          source_id=doc.source_id))

        remaining_text = code_pattern.sub('', text)
        remaining_text = re.sub(r'\n{3,}', '\n\n', remaining_text)
        remaining_text = re.sub(r' +', ' ', remaining_text).strip()

        if not remaining_text:
            return extracted_chunks, None

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description="Extract code blocks and save them as new document").copy(content=ContentType.CHUNK)

        return self._apply_filters(extracted_chunks), self._create_doc(doc, remaining_text, new_metadata)

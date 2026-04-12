from ...core.models import Document, ContentType, Chunk
from ..interfaces import BaseExtractor, BaseFilter
from typing import List, Tuple, Optional, Union
import re

class LinkExtractor(BaseExtractor):
    def __init__(self, filters: List[BaseFilter] = None):
        super().__init__(filters=filters)

    def extract(self, doc: Union[Document, Chunk]) -> Tuple[List[Chunk], Optional[Union[Document, Chunk]]]:
        text = doc.page_content

        # Search for Markdown links: [Link Text](https://url.com)
        link_pattern = re.compile(r'\[([^]]+)]\((https?://[^\s)]+)(?:\s+"[^"]*")?\)')
        extracted_chunks = []

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description="Extract urls and save them as new document").copy(content_type=ContentType.LINK)

        for match in link_pattern.finditer(text):
            link_text = match.group(1)
            url = match.group(2)
            chunk_content = f"{link_text}\nURL: {url}"

            # no chunk index required for extracted text
            extracted_chunks.append(Chunk(page_content=chunk_content,
                                          metadata=new_metadata,
                                          source_id=doc.source_id))

        remaining_text = link_pattern.sub('', text)
        remaining_text = re.sub(r' +', ' ', remaining_text)

        if not remaining_text.strip():
            return extracted_chunks, None

        new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                  component_name=self.name,
                                                  description="Extract links and save them as new document").copy(content=ContentType.CHUNK)

        return self._apply_filters(extracted_chunks), self._create_doc(doc, remaining_text, new_metadata)

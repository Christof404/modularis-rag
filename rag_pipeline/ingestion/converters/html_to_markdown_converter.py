from ...core.models import Document, Metadata, ContentType
from ..interfaces import BaseConverter, BaseFilter
from markdownify import markdownify as md
from typing import List, Tuple, Optional


class HTMLToMarkdownConverter(BaseConverter):
    def __init__(self, filters: List[BaseFilter] = None, **kwargs):
        super().__init__(**kwargs)
        self.filters = filters or []

    def convert(self, doc: Document) -> Optional[Document]:
        metadata =  doc.metadata
        page_content = doc.page_content
        page_text = page_content
        source_id = doc.source_id

        for _filter in self.filters:
            filter_doc = Document(page_content=page_content, metadata=metadata, source_id=source_id)
            result_doc = _filter.process(filter_doc)
            if result_doc is None:
                return None

            page_text = result_doc.page_content
            metadata = result_doc.metadata

        # convert filtered html to markdown
        md_page_content, new_metadata = self._html_to_markdown(page_text, metadata)
        return Document(page_content=md_page_content, metadata=new_metadata, source_id=source_id)

    def _html_to_markdown(self, html: str, metadata: Metadata) -> Tuple[str, Metadata]:
        """
        Converts HTML string to Markdown using markdownify.

        :param html: HTML content
        :return: Markdown formatted string
        """
        converted = md(html,
                       heading_style='ATX',
                       bullets='-',
                       escape_asterisks=True,
                       escape_underscores=True,
                       strip=['script', 'style'])

        metadata = metadata.pipeline_step(component_type=self._type,
                                          component_name=self.name,
                                          description="HTML -> Markdown").copy(content_type=ContentType.MARKDOWN)
        return converted, metadata

from .html_to_markdown_converter import HTMLToMarkdownConverter
from ...core.models import Document, Metadata, ContentType
from typing import List, Tuple, Optional
from ..interfaces import BaseFilter
import requests


class UrlToMarkdownConverter(HTMLToMarkdownConverter):
    """
    Converts HTML content from URLs or raw HTML strings into clean Markdown.
    """

    def __init__(self, timeout: int = 10, verify_ssl: bool = True, filters: List[BaseFilter] = None, **kwargs):
        """
        Initialize the converter with optional request settings.

        :param timeout: Request timeout in seconds
        :param verify_ssl: Whether to verify SSL certificates
        :param filters: List of filters to apply to raw HTML text content
        """

        super().__init__(**kwargs)
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.filters = filters or []

    def convert(self, doc: Document) -> Optional[Document]:
        """
        Converts HTML content from URL to Markdown.

        :param doc: Document with URL in page_content
        :return: New Document with Markdown content
        """

        url = doc.page_content
        html_content, metadata = self._fetch_html(url, doc.metadata)
        if not html_content:
            return None

        # Convert HTML to Markdown
        markdown_content, metadata = self._html_to_markdown(html_content, metadata)

        # return converted doc with new metadata
        return Document(page_content=markdown_content, metadata=metadata, source_id=doc.source_id)

    def _fetch_html(self, url: str, metadata: Metadata) -> Tuple[str, Metadata]:
        """
        Fetches HTML content from a URL.

        :param url: The URL to fetch
        :return: HTML content as string
        """
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'}

        response = requests.get(url,
                                headers=headers,
                                timeout=self.timeout,
                                verify=self.verify_ssl)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        page_text = response.text
        # add pipeline step (url -> html)
        metadata =  metadata.pipeline_step(component_type=self._type,
                                           component_name=self.name,
                                           description="URL -> HTML").copy(content_type=ContentType.HTML)

        for _filter in self.filters:
            filter_doc = Document(page_content=page_text, metadata=metadata, source_id="")
            result_doc = _filter.process(filter_doc)
            if result_doc is None:
                return '', metadata
            page_text = result_doc.page_content
            metadata = result_doc.metadata

        return page_text, metadata

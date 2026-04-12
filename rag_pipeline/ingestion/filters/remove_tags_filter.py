from typing import Optional, Literal, List
from ..interfaces import BaseFilter
from bs4 import BeautifulSoup

class RemoveTagsFilter(BaseFilter):
    def __init__(self, tags_to_remove: List[str] = None, apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        super().__init__(apply_to=apply_to, **kwargs)
        self.tags_to_remove = tags_to_remove or ['style', 'script', 'noscript']

    def process_text(self, text_content: str) -> Optional[str]:
        if not text_content:
            return None

        soup = BeautifulSoup(text_content, 'lxml')

        for tag in self.tags_to_remove:
            for element in soup.find_all(tag):
                element.decompose()

        return str(soup)

    @property
    def metadata_description(self) -> str:
        return f"Removed HTML tags: {', '.join(self.tags_to_remove)}"

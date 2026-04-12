from typing import Optional, Literal
from ..interfaces import BaseFilter
from bs4 import BeautifulSoup



class UniversalHtmlFilter(BaseFilter):
    def __init__(self, apply_to: Literal["page_content", "embed_content", "both"] = "page_content", css_selector: str = 'body', **kwargs):
        super().__init__(apply_to=apply_to, **kwargs)
        self.css_selector = css_selector

    def process_text(self, text_content: str) -> Optional[str]:
        soup = BeautifulSoup(text_content, 'lxml')
        main_content = soup.select_one(self.css_selector)

        if not main_content:
            return None

        return str(main_content)

    @property
    def metadata_description(self) -> str:
        return f"Extracts first HTML element matching CSS selector: '{self.css_selector}'"

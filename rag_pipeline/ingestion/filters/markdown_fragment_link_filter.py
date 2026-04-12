from .regex_replace_filter import RegexReplaceFilter
from typing import Optional, Literal
import re


class MarkdownFragmentLinkFilter(RegexReplaceFilter):
    def __init__(self, apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        pattern = r'(?<!\!)\[[^\[\]]+\]\(\s*#[^\)]*\)'
        super().__init__(pattern=pattern, replacement='', apply_to=apply_to, **kwargs)

    def process_text(self, text_content: str) -> Optional[str]:
        new_text_content = super().process_text(text_content)
        if not new_text_content:
            return None

        new_text_content = re.sub(r' {2,}', ' ', new_text_content)
        new_text_content = re.sub(r'\n{3,}', '\n\n', new_text_content)

        return new_text_content

from typing import Optional, Union, Callable, Literal
from ..interfaces import BaseFilter
import re


class RegexReplaceFilter(BaseFilter):
    def __init__(self, pattern: Union[str, re.Pattern], replacement: Union[str, Callable] = "", apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        super().__init__(apply_to=apply_to, **kwargs)

        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        self.replacement = replacement

    def process_text(self, text_content: str) -> Optional[str]:
        if not text_content:
            return None

        cleaned_text = self.pattern.sub(self.replacement, text_content)
        return cleaned_text

    @property
    def metadata_description(self) -> str:
        return f"Regex replace: {self.pattern.pattern}"

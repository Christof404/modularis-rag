from typing import Optional, Literal
from ..interfaces import BaseFilter


class LengthGuardFilter(BaseFilter):
    def __init__(self, min_chars: int = None, max_chars: int = None, apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        super().__init__(apply_to=apply_to, **kwargs)

        self.min_chars = min_chars or 0
        self.max_chars = max_chars if max_chars is not None else float('inf') # not or, because 0 is evaluated as False

    def process_text(self, text_content: str) -> Optional[str]:
        if len(text_content) < self.min_chars or len(text_content) > self.max_chars:
            return None

        return text_content

    @property
    def metadata_description(self) -> str:
        return f"min:{self.min_chars}, max:{self.max_chars if self.max_chars != float('inf') else 'inf'}"

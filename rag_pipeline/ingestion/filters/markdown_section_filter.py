from typing import Optional, List, Literal
from ..interfaces import BaseFilter
import re


class MarkdownSectionFilter(BaseFilter):
    def __init__(self, sections_to_drop: List[str] = None,
                 apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        super().__init__(apply_to=apply_to, **kwargs)

        self.sections_to_drop = sections_to_drop or []
        self.sections_to_drop_norm = {self._normalize_header(s.lstrip('# ').strip()) for s in self.sections_to_drop}
        self._header_pattern = re.compile(r'^\s*(#{1,6})\s+(.*)$')

    def process_text(self, text_content: str) -> Optional[str]:
        if not self.sections_to_drop_norm:
            return text_content

        lines = text_content.split('\n')
        kept_lines = []
        drop_level = None

        for line in lines:
            match = self._header_pattern.match(line)

            if match:
                level_str, header_text = match.groups()
                current_level = len(level_str)
                normalized_header = self._normalize_header(header_text)

                # Exit drop state when a same/higher level section starts
                if drop_level is not None and current_level <= drop_level:
                    drop_level = None

                # Enter drop state if this header should be dropped
                if drop_level is None and normalized_header in self.sections_to_drop_norm:
                    drop_level = current_level

            if drop_level is None:
                kept_lines.append(line)

        new_text_content = '\n'.join(kept_lines)

        return new_text_content if new_text_content else None

    @staticmethod
    def _normalize_header(text: str) -> str:
        text = text.strip().lower()

        # Remove trailing markdown closing hashes: ## Header ##
        text = re.sub(r'\s+#+\s*$', '', text)

        # Remove MediaWiki edit suffix like:
        # See also[[edit](/w/index.php?...)]
        text = re.sub(r'\s*\[\[.*?]\(.*?\)]\s*$', '', text)

        # Remove simple trailing bracket annotations: Header [foo]
        text = re.sub(r'\s*\[[^]]+]\s*$', '', text)

        return text.strip()

    @property
    def metadata_description(self) -> str:
        return f"Drop sections: [{','.join(self.sections_to_drop)}]"
from .regex_replace_filter import RegexReplaceFilter
from typing import List, Literal
import re


class TextCleanupFilter(RegexReplaceFilter):
    def __init__(self, target_strings: List[str], replacement: str = "", apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        if not target_strings:
            pattern = r'(?!)'
        else:
            # sort the strings in descending order by length!
            # This replaces "[ | ]" with "[" and leaves no half-remnants.
            sorted_strings = sorted(target_strings, key=len, reverse=True)
            escaped_strings = [re.escape(s) for s in sorted_strings]

            # Combine all strings into a pattern using a logical OR (|)
            pattern = f"({'|'.join(escaped_strings)})"

        super().__init__(pattern=pattern, replacement=replacement, apply_to=apply_to, **kwargs)

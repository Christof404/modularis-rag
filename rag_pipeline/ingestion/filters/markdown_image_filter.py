from .regex_replace_filter import RegexReplaceFilter
from urllib.parse import urljoin
from typing import Literal
import requests
import re

class MarkdownImageFilter(RegexReplaceFilter):
    def __init__(self, check_reachability: bool = False, base_url: str = "https://de.wikipedia.org", apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        self.check_reachability = check_reachability
        self.base_url = base_url
        pattern = r'\[?!\[([^\]]*)\]\(([^ \)]+)[^\)]*\)\]?(?:\([^\)]+\))?'

        super().__init__(pattern=pattern, replacement=self._replace_match, apply_to=apply_to, **kwargs)

    def _replace_match(self, match: re.Match) -> str:
        full_match = match.group(0)
        alt_text = match.group(1)
        image_url = match.group(2)

        if self.check_reachability:
            absolute_url = self._get_absolute_url(image_url)

            # check if link is reachable.
            if self._check_url(absolute_url):
                return full_match.replace(image_url, absolute_url, 1)

        return alt_text if alt_text else ""

    def _get_absolute_url(self, url: str) -> str:
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return urljoin(self.base_url, url)
        return url

    @staticmethod
    def _check_url(absolute_url: str) -> bool:
        try:
            response = requests.head(absolute_url, timeout=3, allow_redirects=True, verify=False)
            return response.status_code == 200

        except Exception as e:
            print(f"[ERROR] Failed to check url: {absolute_url}. Message: {e}")
        return False

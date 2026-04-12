from .regex_replace_filter import RegexReplaceFilter
from urllib.parse import urljoin
from typing import Literal
import requests
import re


class MarkdownLinkFilter(RegexReplaceFilter):
    def __init__(self, check_reachability: bool = False, base_url: str = "https://de.wikipedia.org", apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        self.check_reachability = check_reachability
        self.base_url = base_url

        pattern = r'(?<!\!)\[([^\[\]]+)\]\(\s*([^\s\)]+)(?:\s+"[^"]*")?\s*\)'
        super().__init__(pattern=pattern, replacement=self._replace_match, apply_to=apply_to, **kwargs)

    def _get_absolute_url(self, url: str) -> str:
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return urljoin(self.base_url, url)
        return url

    def _replace_match(self, match: re.Match) -> str:
        link_text = match.group(1)
        link_url = match.group(2)

        if self.check_reachability:
            absolute_url = self._get_absolute_url(link_url)
            if self._check_url(absolute_url):
                return f"[{link_text}]({absolute_url})"
            return ''

        absolute_url = self._get_absolute_url(link_url)
        return f"[{link_text}]({absolute_url})"

    @staticmethod
    def _check_url(absolute_url: str) -> bool:
        try:
            response = requests.head(absolute_url, timeout=3, allow_redirects=True, verify=False)
            return response.status_code < 400
        except Exception as e:
            print(f"[ERROR] Failed to check url: {absolute_url}. Message: {e}")
            return False
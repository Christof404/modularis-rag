from ....core.models import Document, Metadata, ContentType, PipelineStep, Pipeline
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Iterator, Optional, List
from datetime import datetime, timezone
from ...interfaces import BaseSource
from collections import deque
from bs4 import BeautifulSoup
import requests
import urllib3
import re

# disable warning for unsecure source link (expect the user know about the source link)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UrlSource(BaseSource):
    def __init__(self, url: str, recursive: bool = False, max_pages: int = 50, max_depth: int = 10, exclude_substrings: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.start_url = url
        self.recursive = recursive
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.exclude_substrings = exclude_substrings or []
        self.base_domain = urlparse(self.start_url).netloc

    def load(self) -> Iterator[Document]:
        if not self.recursive:
            yield self._create_document(self.start_url)
            return

        session = requests.Session()
        seen = set()
        queue = deque([self.start_url])

        while queue and len(seen) < self.max_pages:
            current_url = queue.popleft()
            if current_url in seen:
                continue

            try:
                response = session.get(current_url, timeout=10, verify=False)
                content_type = response.headers.get('Content-Type', '')

                if response.status_code != 200 or 'text/html' not in content_type:
                    continue

            except requests.RequestException:
                continue

            seen.add(current_url)
            yield self._create_document(current_url)

            for link in self._extract_links(response.text, current_url):
                if link not in seen:
                    queue.append(link)

    def _create_document(self, url: str) -> Document:
        metadata = Metadata(title=url,
                            content_type=ContentType.URL,
                            created_on=datetime.now(timezone.utc).isoformat(),
                            pipeline=Pipeline([PipelineStep(component_type=self._type, component_name=self.name)]))
        # Use URL as source_id for stable resume/deduplication
        return Document(page_content=url, metadata=metadata, source_id=url)

    def _extract_links(self, html: str, base_url: str) -> set[str]:
        soup = BeautifulSoup(html, "lxml")
        out = set()

        for a in soup.select("a[href]"):
            href = a["href"]
            full_url = urljoin(base_url, href)

            clean_url = self._normalize(full_url)
            parsed_url = urlparse(clean_url)

            if not self._is_valid_url(clean_url, parsed_url):
                continue

            out.add(clean_url)
        return out

    @staticmethod
    def _normalize(url: str) -> str:
        p = urlparse(url)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, p.query, ""))

    def _is_valid_url(self, url: str, parsed_url) -> bool:
        if parsed_url.scheme not in ('http', 'https'):
            return False
        if parsed_url.netloc != self.base_domain:
            return False

        path_parts = [part for part in parsed_url.path.split('/') if part]
        if len(path_parts) > self.max_depth:
            return False

        for substring in self.exclude_substrings:
            if substring in url:
                return False

        trap_patterns = [r'page=\d+',     # Pagination (?page=2)
                         r'p=\d+',        # Alternative pagination (?p=2)
                         r'sort=',        # Sorting
                         r'filter=',      # Dynamic filters
                         r'date=',        # Calendar/Date
                         r'calendar',     # Calendar paths
                         r'replytocom=']  # WordPress comment replies (common trap)

        for pattern in trap_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        ignore_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.mp4', '.css', '.js')
        if parsed_url.path.lower().endswith(ignore_extensions):
            return False

        return True
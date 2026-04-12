from ..interfaces import BaseConverter
from ...core.models import Document
from typing import Optional


class ByPassConverter(BaseConverter):
    def convert(self, doc: Document) -> Optional[Document]:
        # leaf documents from source unchanged
        return doc

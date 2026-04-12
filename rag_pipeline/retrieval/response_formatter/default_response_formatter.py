from ...core.models import Query, ContextBlock
from ..interfaces import BaseFormatter
from typing import List


class DefaultResponseFormatter(BaseFormatter):
    def __init__(self,  **kwargs):
        super().__init__(**kwargs)

    def format(self, query: Query, context_blocks: List[ContextBlock]) -> str:
        """
        Assembles the final string that is sent to the LLM. (usually as a tool response)
        """
        if not context_blocks:
            return f"Keine relevanten Dokumente in der Datenbank gefunden.\n\n"

        prompt_parts = ["--- GEFUNDENER KONTEXT ---\n\n"]
        for i, block in enumerate(context_blocks, start=1):
            prompt_parts.append(f"QUELLE [{i}]: {block.source_title}\n")
            prompt_parts.append(f"{block.page_content}\n")
            prompt_parts.append("-" * 50 + "\n\n")

        return "".join(prompt_parts)

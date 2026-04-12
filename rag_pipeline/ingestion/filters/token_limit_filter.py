from transformers import AutoTokenizer, PreTrainedTokenizerBase
from typing import Optional, Literal, cast
from ..interfaces import BaseFilter
from enum import Enum
import logging

# Suppress tokenization warnings about sequence length
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)


class TokenLimitMode(str, Enum):
    DROP = "drop"
    TRUNCATE = "truncate"


class TokenLimitFilter(BaseFilter):
    def __init__(self, model_name: str, max_tokens: int, mode: TokenLimitMode = TokenLimitMode.TRUNCATE, prefix="search document:", apply_to: Literal["page_content", "embed_content", "both"] = "page_content", **kwargs):
        super().__init__(apply_to=apply_to, **kwargs)
        self.max_tokens = max_tokens
        self.prefix = prefix.strip()
        self.tokens = []
        self.mode = mode

        self.tokenizer = cast(PreTrainedTokenizerBase, AutoTokenizer.from_pretrained(model_name, trust_remote_code=True))  # cast because of type issues in AutoTokenizer

    def process_text(self, text_content: str) -> Optional[str]:
        # Calculate prefix length to account for it in the limit
        prefix_tokens = self.tokenizer.encode(self.prefix, add_special_tokens=False)
        content_tokens = self.tokenizer.encode(text_content, add_special_tokens=False)
        
        total_len = len(prefix_tokens) + len(content_tokens)

        if total_len <= self.max_tokens:
            return text_content

        if self.mode == TokenLimitMode.DROP:
            print(f"[WARNING]: Chunk dropped (Token limit exceeded: {total_len} > {self.max_tokens})")
            return None

        elif self.mode == TokenLimitMode.TRUNCATE:
            # Calculate how many tokens are left for the content
            allowed_content_tokens = self.max_tokens - len(prefix_tokens)
            if allowed_content_tokens <= 0:
                print(f"[WARNING]: Prefix alone exceeds token limit ({len(prefix_tokens)} > {self.max_tokens})")
                return ""
                
            truncated_content_tokens = content_tokens[:allowed_content_tokens]
            truncated_text = self.tokenizer.decode(truncated_content_tokens, skip_special_tokens=True)

            return truncated_text

    @property
    def metadata_description(self) -> str:
        return f"{self.mode.capitalize()} chunks greater than {self.max_tokens} tokens"

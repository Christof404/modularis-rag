from ..core.models import Chunk, EmbeddingModel, ContentType, EmbeddedChunk
from ..core.base_interfaces import BaseEmbedder
from typing import List
import ollama


class OllamaEmbedder(BaseEmbedder):
    def __init__(self, model_name: str, model_dimension: int, max_tokens: int=512, batch_size: int=64,  prefix_prompt: str="search_document:", **kwargs):
        super().__init__(**kwargs)
        self.model = EmbeddingModel(model_name=model_name,
                                    model_dimension=model_dimension,
                                    max_tokens=max_tokens)
        self.prefix_prompt = prefix_prompt
        self.batch_size = batch_size
        self._ensure_model_exists()

    def _ensure_model_exists(self):
        """Ensures that the specified model exists in Ollama, pulling it if necessary."""
        try:
            ollama.show(self.model.model_name)
        except Exception as e:
            print(f"[WARNING] Model {self.model.model_name} not found or error checking. Attempting to pull... Message: {e}")
            try:
                ollama.pull(self.model.model_name)
                print(f"[INFO] Model {self.model.model_name} pulled successfully.")
            except Exception as pull_err:
                print(f"[ERROR] Failed to pull model {self.model.model_name}: {pull_err}")
                raise pull_err

    def get_prefix(self) -> str:
        return self.prefix_prompt

    def get_model(self) -> EmbeddingModel:
        return self.model

    def embed(self, chunks: List[Chunk]) -> List[EmbeddedChunk]:
        if not chunks:
            return []

        prefix = self.prefix_prompt.strip()
        chunk_contents = []
        for chunk in chunks:
            content = (chunk.embed_content or chunk.page_content or "").strip()
            full_text = f"{prefix} {content}".strip() if prefix else content
            chunk_contents.append(full_text)

        all_embeddings = []

        for i in range(0, len(chunk_contents), self.batch_size):
            batch = chunk_contents[i:i + self.batch_size]
            response = ollama.embed(model=self.model.model_name, input=batch)
            all_embeddings.extend(response["embeddings"])

        embedded_chunks = []
        for chunk_doc, embedding in zip(chunks, all_embeddings):
            new_metadata = chunk_doc.metadata.pipeline_step(component_type=self._type,
                                                            component_name=self.name).copy(content_type=ContentType.EMBEDDING,
                                                                                           model=self.model)

            embedded_chunks.append(EmbeddedChunk(page_content=chunk_doc.page_content,
                                                 embed_content=chunk_doc.embed_content,
                                                 chunk_index=getattr(chunk_doc, 'chunk_index', []),
                                                 embedding=embedding,
                                                 metadata=new_metadata,
                                                 source_id=chunk_doc.source_id))

        return embedded_chunks

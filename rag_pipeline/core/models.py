from __future__ import annotations

from pydantic import GetCoreSchemaHandler
from datetime import datetime, timezone
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from pydantic_core import core_schema
from rich.markup import escape
from rich.table import Table
from enum import Enum
import uuid


class ContentType(str, Enum):
    URL = "url"
    PATH = "path"
    LINK = "link"
    CODE = "code"
    HTML = "html"
    TEXT = "text"
    CHUNK = "chunk"
    TABLE = "table"
    MARKDOWN = "markdown"
    EMBEDDING = "embedding"

    def __str__(self) -> str:
        return self.value


class ChunkStatus(str, Enum):
    RETRIEVED = "retrieved"
    FILTERED_BY_THRESHOLD = "filtered_by_score"
    DROPPED_BY_RERANKER = "dropped_by_reranker"
    SELECTED_FOR_CONTEXT = "selected"
    MERGED = "merged"

    def __str__(self) -> str:
        return self.value

class PipelineStep(BaseModel):
    component_type: str                # "Source", "Filter", "Chunker", "Embedder"
    component_name: str                # Class Names
    description: Optional[str] = None  # example: "url -> html"

    def __repr__(self) -> str:
        if self.description:
            return f"{self.component_type}:{self.component_name} ({self.description})"
        return f"{self.component_type}:{self.component_name}"


class Pipeline(list):
    def __str__(self) -> str:
        if not self:
            return "empty pipeline"
        return " -> ".join(f"{step.component_type}:{step.component_name}" for step in self)

    def __rich_console__(self, *_):
        if not self:
            yield "empty pipeline"
            return

        table = Table(title="Pipeline Workflow",
                      show_header=True,
                      header_style="bold cyan")

        table.add_column("#", style="dim", justify="right", width=3)
        table.add_column("Type", style="magenta")
        table.add_column("Component", style="green", no_wrap=True)
        table.add_column("Description", style="yellow")

        for i, step in enumerate(self, 1):
            desc = escape(str(step.description)) if step.description else "-"
            table.add_row(str(i), str(step.component_type), str(step.component_name), desc)

        yield table

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(lambda v: cls(v), core_schema.list_schema(handler.generate_schema(PipelineStep)))

class EmbeddingModel(BaseModel):
    model_name: str
    model_dimension: int
    max_tokens: int = 512

class Metadata(BaseModel):
    content_type: ContentType
    created_on: str
    title: Optional[str] = None
    header: Optional[dict] = None
    model: Optional[EmbeddingModel] = None        # example: bge_m3, only set after  Embedding step
    pipeline: Pipeline = Field(default_factory=Pipeline)

    def copy(self, **kwargs) -> Metadata:
        return self.model_copy(update=kwargs)

    def pipeline_step(self, component_type: str, component_name: str, description: Optional[str] = None) -> Metadata:
        new_step = PipelineStep(component_type=component_type,
                                component_name=component_name,
                                description=description)
        new_pipeline = Pipeline(self.pipeline + [new_step])
        return self.copy(pipeline=new_pipeline)


class Document(BaseModel):
    # unique source id (different id for each source document (e.g. each url) -> Multiple chunks may get the same id
    source_id: str

    # unique document id, also for every chunk unique
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # page content text which is going to be embedded
    page_content: str

    # Normally none. If not, embed_content is embedded by the embedder instead of page_content.
    # However, embed_content will never end up in the database.
    embed_content: Optional[str] = None

    # default is a basic dict instead of None
    metadata: Metadata = Field(default_factory=lambda: Metadata(content_type=ContentType.TEXT,
                                                                created_on=datetime.now(timezone.utc).isoformat(),
                                                                pipeline=Pipeline()))


class Chunk(Document):
    # save chunk index -> required maybe later in retrieval for context building
    chunk_index: Optional[List[int]] = Field(default_factory=list)

class EmbeddedChunk(Chunk):
    # implement embedding additionally to default chunk
    embedding: Optional[List[float]] = None

class ScoredChunk(EmbeddedChunk):
    score: float
    rank: Optional[int] = None
    status: ChunkStatus = ChunkStatus.RETRIEVED

    # Optional: Saves the original DB score if the reranker overwrites the score.
    db_similarity_score: Optional[float] = None


class ContextBlock(BaseModel):
    """
    An aggregated text block consisting of multiple ScoredChunks from the same source.
    Ready to be passed from the formatter to the LLM.
    """
    page_content: str
    source_title: str

    max_score: float

    # Save original retrieved chunks
    original_chunks: List[ScoredChunk] = Field(default_factory=list)


class Query(BaseModel):
    text: str
    embedding: Optional[List[float]] = None
    filters: Optional[dict] = Field(default_factory=dict)

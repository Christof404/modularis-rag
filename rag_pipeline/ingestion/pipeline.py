from .interfaces import BaseSource, BaseConverter, BaseFilter, BaseChunker, BaseDatabaseWriter
from ..core.metrics import BasePerformanceTracker, NullTracker
from ..core.base_interfaces import BasePipeline, BaseEmbedder
from typing import List, Iterator, Optional, Tuple, Any
from ..core.models import Chunk
import signal


class IngestPipeline(BasePipeline):
    def __init__(self,
                 source: BaseSource,
                 converter: BaseConverter,
                 embedder: BaseEmbedder,
                 filters: List[BaseFilter] = None,
                 chunkers: List[BaseChunker] = None,
                 writer: BaseDatabaseWriter = None,
                 tracker: Optional[BasePerformanceTracker] = None):

        self.writer = writer
        self.source = source
        self.embedder = embedder
        self.converter = converter
        self.filters = filters or []
        self.chunkers = chunkers or []
        self.total_documents_processed = 0
        self.tracker = tracker or NullTracker()  # use NullTracker if no performance tracker is provided

        # Graceful Shutdown
        self._stop_requested = False
        try:
            signal.signal(signal.SIGINT, self._handle_stop_signal)
        except ValueError:
            # Fallback if the pipeline is not running in the main thread (normally not required)
            pass

    def _handle_stop_signal(self, *_):
        """Runs if CTRL+C is pressed."""
        print("\n\nStop signal received! Finalizing document, committing status, and shutdown.")
        self._stop_requested = True

    @staticmethod
    def get_build_info() -> List[Tuple[str, Any]]:
        return [("source", BaseSource),
                ("converter", BaseConverter),
                ("filters", List[Optional[BaseFilter]]),
                ("chunkers", List[BaseChunker]),
                ("embedder", BaseEmbedder),
                ("writer", BaseDatabaseWriter)]

    def get_tracker(self) -> BasePerformanceTracker:
        return self.tracker

    def get_total_documents_processed(self):
        return self.total_documents_processed

    def run(self) -> Iterator[Chunk]:
        with self.tracker.measure("Pipeline", "Total_Run"):
            # load is an iterator, so measure performance inside
            processed_in_this_run = 0
            for doc in self.source.load():
                self.total_documents_processed += 1
                if self._stop_requested:
                    print(f"Pipeline successfully halted. Total documents processed in this run: {processed_in_this_run}.")
                    break

                # Robust resume: check if source_id is already in DB (hash or url based)
                if self.writer and self.writer.is_processed(doc.source_id):
                    continue

                # track progress
                processed_in_this_run += 1

                # 1. converter
                with self.tracker.measure(self.converter.get_identifier().get("type"), self.converter.name):
                    converted_doc = self.converter.convert(doc)
                if not converted_doc:
                    continue

                # 2. filters
                current_doc = converted_doc
                for _filter in self.filters:
                    with self.tracker.measure(_filter.get_identifier().get("type"), _filter.name):
                        current_doc = _filter.process(current_doc)
                    if current_doc is None:
                        break

                if current_doc is None:
                    continue

                # 3. chunkers
                current_chunks = [current_doc]
                for chunker in self.chunkers:
                    next_level_chunks = []
                    for chunk in current_chunks:
                        with self.tracker.measure(chunker.get_identifier().get("type"), chunker.name):
                            next_level_chunks.extend(chunker.chunk(chunk))
                    current_chunks = next_level_chunks

                if not current_chunks:
                    continue

                # 4. embedder
                with self.tracker.measure(self.embedder.get_identifier().get("type"), self.embedder.name):
                    embedded_chunks = self.embedder.embed(current_chunks)

                # 5. write to vector database
                if self.writer and embedded_chunks:
                    with self.tracker.measure(self.writer.get_identifier().get("type"), self.writer.name):
                        self.writer.write(embedded_chunks)

                # 6. Yield to caller
                for chunk in embedded_chunks:
                    yield chunk

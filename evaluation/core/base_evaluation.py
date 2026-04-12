from rag_pipeline.retrieval.pipeline import RetrievalPipeline
from .base_interfaces import BasePerformanceMetric
from .metrics_calculator import MetricsCalculator
from abc import ABC, abstractmethod
from typing import Any
from tqdm import tqdm


class BaseEvaluation(ABC):
    def __init__(self,
                 retrieval_pipeline: RetrievalPipeline,
                 metrics: list[BasePerformanceMetric],
                 num_test_samples: int | None = None,
                 use_only_required_docs: bool = False,
                 passage_threshold: float = 0.7,
                 questions: dict[str, Any] | None = None):

        self.use_only_required_docs = use_only_required_docs
        self.retrieval_pipeline = retrieval_pipeline
        self.metrics = metrics
        self.num_test_samples = num_test_samples
        self.questions = questions
        self.passage_threshold = passage_threshold

    @abstractmethod
    def _load_questions(self) -> dict[str, Any]:
        """
        Returns a dictionary: { "question": ["id1", "id2"] } 
        OR { "question": {"doc_ids": ["id1"], "passage": "text"} }
        """
        pass

    def get_questions(self) -> dict[str, Any]:
        """
        Public method to load and return questions for external management (e.g. for scaling).
        """
        return self._load_questions()

    @staticmethod
    def _get_unique_source_ids(scored_chunks) -> list[str]:
        """
        Extracts unique source_ids from scored chunks to measure document-level performance.
        """
        retrieved_doc_ids = []
        seen = set()
        for chunk in scored_chunks:
            if chunk.source_id not in seen:
                retrieved_doc_ids.append(chunk.source_id)
                seen.add(chunk.source_id)
        return retrieved_doc_ids

    def run(self, progress_callback=None, steps: list[int] | None = None) -> dict | list[dict]:
        # Use preloaded questions or load them now
        questions_to_data = self.questions if self.questions is not None else self._load_questions()
        results = []
        summaries = []
        metrics_calculator = MetricsCalculator(metrics=self.metrics, passage_threshold=self.passage_threshold)

        # Handle num_test_samples early or use max(steps)
        limit = self.num_test_samples
        if steps:
            limit = max(steps)
            steps_set = set(steps)
        else:
            steps_set = set()

        if limit is not None:
            # slice the questions dict
            keys = list(questions_to_data.keys())[:limit]
            questions_to_data = {k: questions_to_data[k] for k in keys}

        filter_dict = {}
        if self.use_only_required_docs:
            # Flatten the list of lists of doc_ids and deduplicate
            required_ids = set()
            for data in questions_to_data.values():
                if isinstance(data, dict):
                    doc_list = data.get("doc_ids", [])
                else:
                    doc_list = data
                for doc_id in doc_list:
                    required_ids.add(doc_id)
            filter_dict = {"source_id": list(required_ids)}

        total_iters = len(questions_to_data)
        
        # Disable tqdm if a progress_callback is provided to avoid overlapping bars
        disable_tqdm = progress_callback is not None
        failed_queries_sample = []
        max_failed_samples = 20 # Limit to avoid bloated files

        for cnt, (question, data) in enumerate(tqdm(questions_to_data.items(), 
                                                               total=total_iters, 
                                                               desc="Evaluation Progress",
                                                               disable=disable_tqdm)):
            
            # Extract expected data
            if isinstance(data, dict):
                expected_doc_ids = data.get("doc_ids", [])
                expected_passage = data.get("passage", None)
            else:
                expected_doc_ids = data
                expected_passage = None

            scored_chunks = self.retrieval_pipeline.run(query_text=question,
                                                        filters_dict=filter_dict,
                                                        evaluation_mode=True)
            
            # Map chunks to unique source_ids
            retrieved_doc_ids = self._get_unique_source_ids(scored_chunks)
            metrics_results = metrics_calculator.add_query_result(retrieved_doc_ids, 
                                                                 expected_doc_ids,
                                                                 retrieved_chunks=scored_chunks,
                                                                 expected_passage=expected_passage)

            # Collect failed query sample
            if not metrics_results["matches"] and len(failed_queries_sample) < max_failed_samples:
                top_mistake = scored_chunks[0].metadata.title if scored_chunks else "N/A"
                failed_queries_sample.append({"question": question,
                                              "expected_ids": expected_doc_ids,
                                              "top_mistake": top_mistake})

            results.append({"question": question,
                            "expected_doc_ids": expected_doc_ids,
                            "retrieved_doc_ids": retrieved_doc_ids,
                            **metrics_results})
            
            current_count = cnt + 1
            if current_count in steps_set:
                summary = metrics_calculator.get_summary()
                summary["num_samples"] = current_count
                summary["failed_queries_sample"] = list(failed_queries_sample) # snapshot of current failures
                summaries.append(summary)

            if progress_callback:
                progress_callback()

        if steps:
            # Ensure summaries are sorted by sample count
            summaries.sort(key=lambda x: x.get("num_samples", 0))
            return summaries

        summary = metrics_calculator.get_summary()
        summary["num_samples"] = len(results)
        summary["results"] = results
        summary["failed_queries_sample"] = failed_queries_sample
        return summary

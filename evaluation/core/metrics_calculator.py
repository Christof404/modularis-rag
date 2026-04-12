from rag_pipeline.retrieval.interfaces import ScoredChunk
from .base_interfaces import BasePerformanceMetric
from typing import List, Dict, Any
import string
import re



class MetricsCalculator:
    def __init__(self, metrics: List[BasePerformanceMetric], ks: List[int] = None, passage_threshold: float = 0.7):
        """
        Initializes the MetricsCalculator with a list of metric objects.
        :param metrics: List of metric instances that implement BasePerformanceMetric.
        :param ks: List of k values to evaluate at (default [1, 3, 5, 10]).
        :param passage_threshold: Threshold for passage-level success (0.0 to 1.0).
        """
        self.passage_threshold = passage_threshold
        self.ks = ks or [1, 3, 5, 10]
        self.total_expected = 0
        self.metrics = metrics
        self.num_processed = 0
        self.total_matches = 0

        # Data structure: { "MetricName": { k: total_value } }
        self.accumulated_results = {metric.name: {k: 0.0 for k in self.ks} for metric in self.metrics}
        
        # Passage-level results: { k: count_success }
        self.passage_success_counts = {k: 0 for k in self.ks}
        self.has_passage_data = False

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        # Lowercase
        text = text.lower()
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _calculate_passage_overlap(self, retrieved_text: str, expected_text: str) -> float:
        """
        Calculates how much of the retrieved text is contained in the expected text.
        This is more robust for RAG where chunks are often smaller than the full ground truth passage.
        """
        norm_retrieved = self._normalize_text(retrieved_text)
        norm_expected = self._normalize_text(expected_text)
        
        if not norm_expected:
            return 1.0
            
        retrieved_words = set(norm_retrieved.split())
        expected_words = set(norm_expected.split())
        
        if not retrieved_words:
            return 0.0
            
        common = retrieved_words.intersection(expected_words)
        
        # Precision: What percentage of the retrieved chunk is 'correct' (exists in ground truth)?
        return len(common) / len(retrieved_words)

    def add_query_result(self, 
                         retrieved_doc_ids: List[str], 
                         expected_doc_ids: List[str],
                         retrieved_chunks: List[ScoredChunk] = None,
                         expected_passage: str = None) -> Dict[str, Any]:
        """
        Evaluates a single query against all registered metrics and optionally passage-level success.
        """
        expected_set = set(expected_doc_ids)
        retrieved_tuple = tuple(retrieved_doc_ids)
        expected_tuple = tuple(expected_doc_ids)

        matches_all = [doc_id for doc_id in retrieved_doc_ids if doc_id in expected_set]
        self.total_matches += len(matches_all)
        self.total_expected += len(expected_set)
        self.num_processed += 1

        query_metrics_at_k = {k: {} for k in self.ks}

        # Document-level metrics
        for metric_obj in self.metrics:
            metric_name = metric_obj.name
            results = metric_obj.evaluate(retrieved_tuple, expected_tuple, self.ks)

            for res in results:
                self.accumulated_results[metric_name][res.k] += res.result
                query_metrics_at_k[res.k][metric_name] = res.result

        # Passage-level evaluation
        passage_results = {}
        if expected_passage and retrieved_chunks:
            self.has_passage_data = True
            for k in self.ks:
                # Check top k chunks
                chunks_to_check = retrieved_chunks[:k]
                max_overlap = 0.0
                for chunk in chunks_to_check:
                    overlap = self._calculate_passage_overlap(chunk.page_content, expected_passage)
                    max_overlap = max(max_overlap, overlap)
                
                is_success = max_overlap >= self.passage_threshold
                if is_success:
                    self.passage_success_counts[k] += 1
                
                passage_results[k] = {"max_overlap": max_overlap,
                                      "success": is_success}

        return {"matches": matches_all,
                "num_matches": len(matches_all),
                "num_expected": len(expected_set),
                "metrics_at_k": query_metrics_at_k,
                "passage_results": passage_results if self.has_passage_data else None}

    def get_summary(self) -> Dict[str, Any]:
        """
        Returns the averaged metrics across all processed queries.
        """
        if self.num_processed == 0:
            return {"error": "No data processed"}

        summary = {"total_questions_evaluated": self.num_processed,
                   "total_matches_global": self.total_matches,
                   "total_expected_doc_ids_global": self.total_expected,
                   "global_recall": self.total_matches / self.total_expected if self.total_expected > 0 else 0,
                   "available_metrics": list(self.accumulated_results.keys()),
                   "has_passage_evaluation": self.has_passage_data}

        # Doc-level summaries
        for metric_name, ks_dict in self.accumulated_results.items():
            for k, total_val in ks_dict.items():
                summary[f"{metric_name}@{k}"] = total_val / self.num_processed

        # Passage-level summaries
        if self.has_passage_data:
            summary["passage_metrics"] = ["passage_success"]
            for k, count in self.passage_success_counts.items():
                summary[f"passage_success@{k}"] = count / self.num_processed

        return summary

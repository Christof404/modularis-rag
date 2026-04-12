from rag_pipeline.retrieval.registry import REGISTRY as RETRIEVAL_REGISTRY
from rag_pipeline.retrieval.pipeline import RetrievalPipeline
from rag_pipeline.core.base_interfaces import BasePipeline
from rag_pipeline.core.registry import ComponentRegistry
from rag_pipeline.core.metrics import PipelineTracker
from rag_pipeline.core.factory import Factory
from typing import List, Tuple, Any, Callable
from .registry import REGISTRY
import json


class EvaluationPipeline(BasePipeline):
    def __init__(self):
        self.evaluation = None

    @staticmethod
    def get_build_info() -> List[Tuple[str, Any]]:
        return []

    def get_tracker_report(self) -> str:
        if not self.evaluation or not self.evaluation.retrieval_pipeline:
            return "No tracker results available"

        tracker = self.evaluation.retrieval_pipeline.get_tracker()
        if hasattr(tracker, "get_report"):
            return tracker.get_report()
        return "Tracker does not support get_report()"

    def print_tracker_report(self):
        print(self.get_tracker_report())

    @staticmethod
    def load_retrieval_pipeline(config_path: str) -> RetrievalPipeline:
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)

        return EvaluationPipeline.load_retrieval_pipeline_from_dict(config_dict)

    @staticmethod
    def load_retrieval_pipeline_from_dict(config_dict: dict) -> RetrievalPipeline:
        registry = ComponentRegistry(RETRIEVAL_REGISTRY)
        factory = Factory(registry)

        components = {key: factory.instantiate_from_config(cfg) for key, cfg in config_dict.items()}
        pipeline = RetrievalPipeline(embedder=components.get("embedder"),
                                     retriever=components.get("retriever"),
                                     context_builder=components.get("context_builder"),
                                     formatter=components.get("formatter"),
                                     pre_filters=components.get("pre_filters", []),
                                     reranker=components.get("reranker"),
                                     post_filters=components.get("post_filters", []),
                                     tracker=PipelineTracker())
        return pipeline

    def run(self, evaluation_source, evaluation_parameters, progress_callback=None) -> dict:
        eval_class = REGISTRY["sources"][evaluation_source]

        evaluation = eval_class(**evaluation_parameters)
        summary = evaluation.run(progress_callback=progress_callback)

        return summary

    @staticmethod
    def run_scaling(evaluation_source: str,
                    base_parameters: dict, 
                    steps: List[int], 
                    progress_callback: Callable = None) -> List[dict]:
        """
        Runs evaluation for multiple sample sizes (steps) incrementally.
        Pre-loads questions efficiently once and avoids redundant evaluations.
        """
        source_class = REGISTRY["sources"][evaluation_source]
        
        # 1. Prepare parameters for the evaluation run
        current_params = base_parameters.copy()
        current_params["num_test_samples"] = max(steps)
        
        # 2. Instantiate and run incrementally
        evaluation = source_class(**current_params)
        all_summaries = evaluation.run(progress_callback=progress_callback, steps=steps)

        return all_summaries

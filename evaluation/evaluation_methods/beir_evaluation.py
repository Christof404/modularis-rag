from rag_pipeline.retrieval.pipeline import RetrievalPipeline
from ..core.base_interfaces import BasePerformanceMetric
from beir.datasets.data_loader import GenericDataLoader
from ..core.base_evaluation import BaseEvaluation
from typing import Any


class BeirEvaluation(BaseEvaluation):
    def __init__(self, 
                 dataset_path: str, 
                 retrieval_pipeline: RetrievalPipeline, 
                 metrics: list[BasePerformanceMetric],
                 num_test_samples: int | None = None, 
                 use_only_required_docs: bool = False,
                 questions: dict[str, Any] | None = None):
        super().__init__(retrieval_pipeline=retrieval_pipeline, 
                         metrics=metrics,
                         num_test_samples=num_test_samples, 
                         use_only_required_docs=use_only_required_docs,
                         questions=questions)
        self.dataset_path = dataset_path


    def _load_questions(self) -> dict[str, Any]:
        _, queries, q_rels = GenericDataLoader(data_folder=self.dataset_path).load(split="test")
        question_to_doc_ids = {queries[qid]: list(doc_dict.keys()) for qid, doc_dict in q_rels.items()}
        return question_to_doc_ids

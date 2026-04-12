from rag_pipeline.retrieval.pipeline import RetrievalPipeline
from ..core.base_interfaces import BasePerformanceMetric
from ..core.base_evaluation import BaseEvaluation
from datasets import load_dataset
from typing import Any

class GoogleNQEvaluation(BaseEvaluation):
    def __init__(self, 
                 retrieval_pipeline: RetrievalPipeline, 
                 metrics: list[BasePerformanceMetric],
                 num_test_samples: int | None = None, 
                 use_only_required_docs: bool = False, 
                 split: str = "validation",
                 questions: dict[str, Any] | None = None):
        super().__init__(retrieval_pipeline=retrieval_pipeline,
                         metrics=metrics,
                         num_test_samples=num_test_samples,
                         use_only_required_docs=use_only_required_docs,
                         questions=questions)
        self.split = split


    def _load_questions(self) -> dict[str, list[str]]:
        dataset = load_dataset("google-research-datasets/natural_questions",
                               split=self.split,
                               streaming=True)

        questions_to_doc_ids = {}
        count = 0
        for item in dataset:
            if self.num_test_samples is not None and count >= self.num_test_samples:
                break

            doc_id = item["document"]["url"]
            question = item["question"]["text"]

            if question not in questions_to_doc_ids:
                questions_to_doc_ids[question] = [doc_id]
                count += 1
            else:
                if doc_id not in questions_to_doc_ids[question]:
                    questions_to_doc_ids[question].append(doc_id)

        return questions_to_doc_ids

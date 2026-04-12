from ....core.models import Document, Metadata, ContentType, PipelineStep, Pipeline
from datetime import datetime, timezone
from ...interfaces import BaseSource
from datasets import load_dataset
from typing import Iterator


class GoogleNQSource(BaseSource):
    def __init__(self, num_samples: int = 1000, split: str = "validation", **kwargs):
        super().__init__(**kwargs)
        self.num_samples = num_samples
        self.split = split

    def load(self) -> Iterator[Document]:
        dataset = load_dataset("google-research-datasets/natural_questions",
                               split=self.split,
                               streaming=True)

        seen_docs = set()
        count = 0
        for item in dataset:
            if count >= self.num_samples:
                break

            html_content = item["document"]["html"]
            title = item["document"]["title"]
            doc_id = item["document"]["url"]

            if doc_id in seen_docs:
                continue

            seen_docs.add(doc_id)
            metadata = Metadata(title=title,
                                content_type=ContentType.HTML,
                                created_on=datetime.now(timezone.utc).isoformat(),
                                pipeline=Pipeline([PipelineStep(component_type=self._type, component_name=self.name)]))

            yield Document(page_content=html_content,
                           metadata=metadata,
                           source_id=doc_id)

            count += 1


def main():
    source = GoogleNQSource(num_samples=50)
    for cnt, item in enumerate(source.load()):
        print(f"cnt: {cnt}: {item.page_content[:10]}...")

if __name__ == '__main__':
    main()

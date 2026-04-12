from ....core.models import Document, Metadata, ContentType, PipelineStep, Pipeline
from beir.datasets.data_loader import GenericDataLoader
from datetime import datetime, timezone
from ...interfaces import BaseSource
from typing import Iterator
from beir import util
import pathlib
import os


class BEIRSource(BaseSource):
    def __init__(self, dataset: str, **kwargs):
        super().__init__(**kwargs)
        self.dataset_url = f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{dataset}.zip"
        self.output_path =  os.path.join(pathlib.Path(__file__).parent.absolute(), "datasets")

        # download and unzip dataset
        self.data_path = self._download_and_unzip()


    def load(self) -> Iterator[Document]:
        corpus, _, _ = GenericDataLoader(data_folder=self.data_path).load(split="test")
        for key in corpus.keys():
            metadata = Metadata(title=str(key),
                                content_type=ContentType.TEXT,
                                created_on=datetime.now(timezone.utc).isoformat(),
                                pipeline=Pipeline([PipelineStep(component_type=self._type, component_name=self.name)]))

            doc_id = str(key)
            page_content = corpus[key].get("text")
            yield Document(page_content=page_content,
                           metadata=metadata,
                           source_id=doc_id)

    def _download_and_unzip(self):
        return util.download_and_unzip(self.dataset_url, self.output_path)

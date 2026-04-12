"""
Experimental RAPTOR-inspired hierarchical chunker.
 inspired by:
Sarthi et al. (2024), "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval"

Implemented idea:
1. Create leaf chunks using a base chunker.
2. Embed chunks at the current hierarchy level.
3. Cluster embeddings using UMAP dimensionality reduction + Gaussian Mixture Model
   (GMM), with BIC-based model selection.
4. Build parent nodes by LLM summarization of each cluster.
5. Repeat recursively for multiple levels.

Important: This is NOT a faithful reproduction of the original RAPTOR method.

Main deviations from the RAPTOR paper:
- Leaf generation:
  Leaves are created by a configurable base chunker, not the exact leaf chunker from the paper's pipeline

- Clustering strategy:
  This implementation is a single stage UMAP -> GMM per hierarchy level.
  It does NOT implement the paper's explicit global-then-local two-stage clustering procedure.

- Hierarchy control / stopping criteria:
  Recursion is bounded by practical engineering parameters (e.g., min_chunks, max_levels, and a minimum number of nodes per level).
  This is not the exact stopping behavior described in the paper.

- Soft cluster assignment:
  Chunks are assigned to all clusters whose posterior probability exceeds a threshold,
  with argmax fallback if none exceeds the threshold. This can produce overlapping and not a strict disjoint tree.

- Summarization step:
  Cluster contents are concatenated and summarized directly with an LLM using a
  custom prompt, which is not the correct prompt from the paper, and structured output.
  It also does not perform token-budget-aware rechunking of oversized clusters before summarization.

- LLM backend:
  Summaries are generated through a local llm client and model selection, rather than the exact model used in the paper.
"""

from ...interfaces import BaseChunker, BaseFilter, BaseExtractor
from ....core.models import Document, ContentType, Chunk
from ....core.base_interfaces import BaseEmbedder
from sklearn.mixture import GaussianMixture
from typing import List, Dict, Union
from dataclasses import dataclass
from pydantic import BaseModel
import numpy as np
import ollama
import umap
import json


@dataclass(frozen=True)
class RaptorParameters:
    cluster_threshold: float
    gmm_covariance_type: str
    reduction_dimension: int
    max_n_neighbors: int
    umap_metric: str
    random_seed: int
    min_chunks: int
    max_levels: int

class Summary(BaseModel):
    summary: str

class ExperimentalRaptorChunker(BaseChunker):
    def __init__(self,
                 base_chunker: BaseChunker,
                 embedder: BaseEmbedder,
                 llm_model_name: str = 'gpt-oss:20b',
                 raptor_params: RaptorParameters = None,
                 filters: List[BaseFilter] = None,
                 extractors: List[BaseExtractor] = None,
                 target_content_types: List[ContentType] = None,
                 **kwargs):
        super().__init__(filters, extractors, **kwargs)

        self.target_content_types = target_content_types or [ContentType.TEXT, ContentType.CHUNK, ContentType.MARKDOWN]
        self.raptor_params = raptor_params or RaptorParameters(cluster_threshold=0.2,
                                                               gmm_covariance_type='full',
                                                               reduction_dimension=10,
                                                               max_n_neighbors=15,
                                                               umap_metric='cosine',
                                                               random_seed=42,
                                                               min_chunks=10,
                                                               max_levels=3)
        self.llm_model_name = llm_model_name
        self.base_chunker = base_chunker
        self.embedder = embedder

        self.client = ollama.Client()

    def chunk(self, doc: Union[Document, Chunk]) -> List[Chunk]:
        # only chunks allowed docs
        current_type = getattr(doc.metadata, 'content_type', ContentType.TEXT)
        if current_type not in self.target_content_types:
            return [doc]

        # 0. run extractors:
        extractor_chunks, doc = self._apply_extractors(doc)
        if not doc:
            return self._apply_filters(extractor_chunks)

        # 1. create leaf nodes (chunk document with base chunker)
        leaf_chunks = self.base_chunker.chunk(doc)
        all_tree_chunks = list(leaf_chunks)
        all_tree_chunks = extractor_chunks + all_tree_chunks

        if len(leaf_chunks) < self.raptor_params.min_chunks:
            print(f"[WARNING] Document too short for RAPTOR ({len(leaf_chunks)} Chunks, "
                  f"MIN: {self.raptor_params.min_chunks} required). Skip tree generation.")
            return self._apply_filters(all_tree_chunks)

        current_level_chunks = leaf_chunks
        chunk_index_list = self._get_chunk_index_list(doc)

        # 2. recursive tree building (Bottom-Up)
        for level in range(1, self.raptor_params.max_levels + 1):
            num_chunks = len(current_level_chunks)
            if num_chunks <= 3:
                # Too few chunks for meaningful clustering
                break

            # create embeddings for current tree level
            embedded_chunks = self.embedder.embed(current_level_chunks)
            embeddings_array = np.array([c.embedding for c in embedded_chunks])

            # 3. Clustering according to RAPTOR paper (UMAP + GMM with BIC optimization)
            clusters = self._perform_raptor_clustering(embeddings_array)

            next_level_chunks = []
            # 4. LLM summarizes the found clusters
            for inner_index, (cluster_id, chunk_indices) in enumerate(clusters.items()):
                cluster_texts = [current_level_chunks[i].page_content for i in chunk_indices]
                # paper would chunk it again if it were too large. Assume that chunks are small enough due to hierarchical chunking by the base chunker and possibly preceding chunker.
                joined_text = "\n---\n".join(cluster_texts)

                # set unique ids for tree tracking
                actual_child_ids = [current_level_chunks[i].document_id for i in chunk_indices]
                summary = self._summarize_cluster(joined_text)

                if summary:
                    new_metadata = doc.metadata.pipeline_step(component_type=self._type,
                                                              component_name=self.name,
                                                              description=f"raptor_level: {level}, "
                                                                          f"cluster: {cluster_id},"
                                                                          f"child_ids: {actual_child_ids},"
                                                                          f"reduction_dimension: {self.raptor_params.reduction_dimension},"
                                                                          f"cluster threshold: {self.raptor_params.cluster_threshold}").copy(content_type=ContentType.CHUNK)

                    parent_doc = Chunk(page_content=summary,
                                       chunk_index=chunk_index_list + [-level, inner_index],  # index will get negative! -> Two values to save tree structure
                                       metadata=new_metadata,
                                       source_id=doc.source_id)
                    next_level_chunks.append(parent_doc)

            all_tree_chunks.extend(next_level_chunks)
            current_level_chunks = next_level_chunks

        return self._apply_filters(all_tree_chunks)

    def _perform_raptor_clustering(self, embeddings: np.ndarray) -> Dict[int, List[int]]:
        """
        UMAP + GMM + BIC inspired from the RAPTOR paper.
        """
        num_samples = embeddings.shape[0]

        n_components = min(self.raptor_params.reduction_dimension, max(2, num_samples - 2))
        n_neighbors = min(self.raptor_params.max_n_neighbors, num_samples - 1)

        # 1. UMAP
        reducer = umap.UMAP(n_neighbors=n_neighbors,
                            n_components=n_components,
                            metric=self.raptor_params.umap_metric,
                            random_state=self.raptor_params.random_seed)
        reduced_embeddings = reducer.fit_transform(embeddings)

        # 2. GMM with BIC optimization
        lowest_bic = np.inf
        best_gmm = None
        max_clusters = max(2, num_samples // 2)

        for n_clusters in range(1, max_clusters + 1):
            gmm = GaussianMixture(n_components=n_clusters,
                                  random_state=self.raptor_params.random_seed,
                                  covariance_type=self.raptor_params.gmm_covariance_type)
            gmm.fit(reduced_embeddings)
            bic_score = gmm.bic(reduced_embeddings)

            if bic_score < lowest_bic:
                lowest_bic = bic_score
                best_gmm = gmm

        # 3. Soft Clustering
        probs = best_gmm.predict_proba(reduced_embeddings)
        n_best_clusters = best_gmm.n_components

        current_proj_clusters = {i: [] for i in range(n_best_clusters)}
        for i in range(num_samples):
            assigned = False
            for cluster_id in range(n_best_clusters):
                if probs[i, cluster_id] > self.raptor_params.cluster_threshold:
                    current_proj_clusters[cluster_id].append(i)
                    assigned = True

            if not assigned:
                best_cluster = int(np.argmax(probs[i]))
                current_proj_clusters[best_cluster].append(i)

        # remove empty clusters
        return {cid: indexes for cid, indexes in current_proj_clusters.items() if indexes}

    def _summarize_cluster(self, text: str) -> str:
        llm_prompt = ("Du bist ein Experte für Textzusammenfassungen. Hier sind mehrere Textabschnitte, "
                      "die semantisch zusammenhängen. Bitte schreibe eine umfassende, neutrale Zusammenfassung "
                      "dieser Abschnitte, die alle wesentlichen Fakten, Entitäten und Zusammenhänge erhält.\n\n"
                      f"<texte>\n{text}\n</texte>\n\n"
                      f"Antworte strikt in folgendem JSON Format: {json.dumps(Summary.model_json_schema())}")

        try:
            response = self.client.chat(messages=[{'role': 'user', 'content': llm_prompt}],
                                        model=self.llm_model_name,
                                        format=Summary.model_json_schema())

            result = Summary.model_validate_json(response.message.content)
            return result.summary

        except Exception as e:
            print(f"[Warning] LLM summary failed (len={len(text)}): {e}")
            return ""

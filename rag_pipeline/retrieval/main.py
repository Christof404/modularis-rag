from ..core.registry import ComponentRegistry
from ..core.metrics import PipelineTracker
from .pipeline import RetrievalPipeline
from ..core.factory import Factory
from .registry import REGISTRY
import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Run the Retrieval Pipeline")
    parser.add_argument("--config",
                        type=str,
                        default="pipeline_config.json",
                        help="Path to the configuration file (default: pipeline_config.json)")
    # 1. Load configuration
    args = parser.parse_args()
    config_path = args.config

    registry = ComponentRegistry(REGISTRY)
    retrieval_factory = Factory(registry)

    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = json.load(f)

    print(f"Load pipeline setup: {config_path}...")

    # 2. Build the real class instances from the JSON dictionary
    components = {key: retrieval_factory.instantiate_from_config(val) for key, val in config_dict.items()}

    # 3. init Pipeline
    pipeline = RetrievalPipeline(embedder=components.get("embedder"),
                                 retriever=components.get("retriever"),
                                 context_builder=components.get("context_builder"),
                                 formatter=components.get("formatter"),
                                 pre_filters=components.get("pre_filters", []),
                                 post_filters=components.get("post_filters", []),
                                 reranker=components.get("reranker"),
                                 tracker=PipelineTracker())
    tracker = pipeline.get_tracker()

    # 4. Sart Pipeline
    query = input("Enter search query: ")
    final_response, context_blocks, plain_chunks = pipeline.run(query_text=query,
                                                                filters_dict={})
    print(f"Final response:\n {final_response}")
    # print(f"Final chunks: {plain_chunks}")

    if hasattr(tracker, "print_report"):
        # Base Traker does not have such function
        tracker.print_report()

if __name__ == '__main__':
    main()

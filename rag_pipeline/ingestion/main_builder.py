from ..pipeline_builder.builder import PipelineBuilder
from ..core.registry import ComponentRegistry
from .pipeline import IngestPipeline
from .registry import REGISTRY
import argparse


def main():
    parser = argparse.ArgumentParser(description="Build new Ingest Pipeline")
    parser.add_argument("--config_save_path",
                        type=str,
                        default="pipeline_config.json",
                        help="Path to save the configuration file (default: pipeline_config.json)")
    args = parser.parse_args()
    config_path = args.config_save_path

    registry = ComponentRegistry(REGISTRY)
    builder = PipelineBuilder(config_path, IngestPipeline, registry)
    builder.build()


if __name__ == '__main__':
    main()

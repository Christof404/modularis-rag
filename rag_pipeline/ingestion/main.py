from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from ..core.registry import ComponentRegistry
from ..core.metrics import PipelineTracker
from .pipeline import IngestPipeline
from ..core.factory import Factory
from rich.console import Console
from .registry import REGISTRY
from rich.panel import Panel
import argparse
import json

DEBUG = False

def main():
    parser = argparse.ArgumentParser(description="Run the Ingest Pipeline")
    parser.add_argument("--config",
                        type=str,
                        default="pipeline_config.json",
                        help="Path to the configuration file (default: pipeline_config.json)")
    # 1. Load configuration
    args = parser.parse_args()
    config_path = args.config

    registry = ComponentRegistry(REGISTRY)
    ingest_factory = Factory(registry, config_save_path=f"pipeline_templates/{config_path}.json")

    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = json.load(f)

    print(f"Load pipeline setup: {config_path}...")

    # 2. Build the real class instances from the JSON dictionary
    components_dict = {key: ingest_factory.instantiate_from_config(val) for key, val in config_dict.items()}

    # 3. init Pipeline
    pipeline = IngestPipeline(**components_dict, tracker=PipelineTracker())
    tracker = pipeline.get_tracker()

    # 4. Show Pipeline Configuration
    console = Console()
    console.print(Panel(pipeline.get_pipeline_model(),
                        title=f"[bold cyan]Pipeline Setup: {config_path}[/bold cyan]",
                        border_style="cyan",
                        expand=False))

    # 5. Start Pipeline
    print("\nRun...")
    cur_title = None
    cur_id = None
    processed_count = 0

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn()) as progress:
        task = progress.add_task("Starting...", total=None)

        for final_chunk in pipeline.run():
            if cur_id == final_chunk.source_id:
                if DEBUG:
                    progress.console.print(Panel(final_chunk.page_content,
                                                 title=f"Content: {cur_title}",
                                                 border_style="cyan",
                                                 expand=False))
                continue

            cur_title = final_chunk.metadata.title
            cur_id = final_chunk.source_id
            processed_count += 1

            # Calculate speed
            elapsed = progress.tasks[task].elapsed
            speed = processed_count / elapsed if elapsed > 0 else 0

            progress.update(task,
                            description=f"Processed: [bold green]{pipeline.get_total_documents_processed()}[/bold green] items | Current: [bold blue]{cur_title}[/bold blue] | [yellow]{speed:.2f} doc/s[/yellow] |")
            if DEBUG:
                progress.console.print(Panel(final_chunk.page_content,
                                             title=f"Content: {cur_title}",
                                             border_style="cyan",
                                             expand=False))

    if hasattr(tracker, "print_report"):
        # Base Traker does not have such function
        tracker.print_report()


if __name__ == '__main__':
    main()

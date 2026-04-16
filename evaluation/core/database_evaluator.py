from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from ..pipeline import EvaluationPipeline
from .visualizing import MetricVisualizer
from .reporting import ResultPresenter
from rich.console import Console
from ..registry import REGISTRY
from pathlib import Path
from typing import Any
import psycopg

class DatabaseEvaluator:
    def __init__(self):
        self.pipeline = EvaluationPipeline()
        self.presenter = ResultPresenter()
        self.visualizer = MetricVisualizer()
        self.console = Console()

    @staticmethod
    def _get_tables(dsn: str) -> list[str]:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                return [row[0] for row in cur.fetchall()]

    def _patch_config(self, config: Any, table_name: str) -> Any:
        """Recursively replaces 'table_name' values in the configuration dictionary."""
        if isinstance(config, dict):
            return {k: (table_name if k == "table_name" else self._patch_config(v, table_name)) 
                    for k, v in config.items()}
        elif isinstance(config, list):
            return [self._patch_config(item, table_name) for item in config]
        return config

    def main(self, 
             dsn: str, 
             start_samples: int, 
             end_samples: int, 
             step: int, 
             retrieval_pipeline_json: dict,
             split: str = "validation",
             use_only_required_docs: bool = True,
             metrics_keys: list[str] = None):
        """
        Main entry point for batch evaluation of all tables in a database.
        """
        tables = self._get_tables(dsn)
        metrics = [REGISTRY["metrics"][k]() for k in (metrics_keys or REGISTRY["metrics"].keys())]
        steps = list(range(start_samples, end_samples + 1, step))
        total_questions_per_table = max(steps)

        self.console.print(f"[bold green]Found {len(tables)} tables to evaluate.[/bold green]")

        for table_name in tables:
            if "_" not in table_name:
                self.console.print(f"[yellow]Skipping table '{table_name}' as it does not follow 'method_version' convention.[/yellow]")
                continue

            method_name, version = table_name.split("_", 1)
            
            self.console.rule(f"[bold cyan]Evaluating {method_name} (Version: {version})[/bold cyan]")

            # 1. Patch and Load Pipeline
            patched_config = self._patch_config(retrieval_pipeline_json, table_name)
            retrieval_pipeline = EvaluationPipeline.load_retrieval_pipeline_from_dict(patched_config)

            # 2. Run Scaling Evaluation with Progress Bar
            base_parameters = {"retrieval_pipeline": retrieval_pipeline,
                               "metrics": metrics,
                               "use_only_required_docs": use_only_required_docs,
                               "split": split}
            
            with Progress(SpinnerColumn(),
                          TextColumn("[progress.description]{task.description}"),
                          BarColumn(),
                          TaskProgressColumn(),
                          TimeRemainingColumn(),
                          console=self.console) as progress:
                
                eval_task = progress.add_task(f"[magenta]Processing {table_name}", total=total_questions_per_table)
                
                def update_progress():
                    progress.advance(eval_task)

                all_summaries = self.pipeline.run_scaling(evaluation_source="GoogleNQEvaluation",
                                                          base_parameters=base_parameters,
                                                          steps=steps,
                                                          progress_callback=update_progress)

            # 3. Generate Visuals and Markdown Report
            output_dir = Path(f"src/rag-database/pipeline_evaluations/evaluation/google_nq/all_docs_is_{not use_only_required_docs}/{method_name}/{version}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            plot_filename = "scaling_plot.png"
            plot_path = output_dir / plot_filename
            self.visualizer.create_scaling_plot(all_summaries, plot_path, title=f"Scaling Analysis: {table_name}")

            tracker_report = retrieval_pipeline.get_tracker().get_report()
            md_report = self.presenter.generate_markdown_report(all_summaries,
                                                                tracker_report,
                                                                is_scaling=True,
                                                                plot_filename=plot_filename)

            # 4. Save Results as output.md
            output_path = output_dir / "output.md"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_report)

            self.console.print(f"[green]Report and Plot saved to:[/green] {output_dir}\n")

        self.console.print("[bold green]Batch evaluation completed successfully.[/bold green]")

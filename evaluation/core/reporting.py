from rich.console import Console
from rich.table import Table
from typing import Any

class ResultPresenter:
    """
    Service for displaying evaluation results in a structured and visually appealing way.
    Supports terminal output (Rich) and file output (Markdown).
    """
    def __init__(self, console: Console = None):
        self.console = console or Console()

    def print_evaluation_summary(self, summary: dict):
        # ... (Keep existing terminal print logic for CLI usage)
        self.console.rule("[bold magenta]Evaluation Summary (Document Level)[/bold magenta]")
        table = self._build_rich_table(summary, is_scaling=False)
        self.console.print(table)
        self.console.print(f"\nNumber of evaluated questions: [bold]{summary.get('total_questions_evaluated', 0)}[/bold]")
        self.console.print(f"Global Recall: [bold]{summary.get('global_recall', 0):.3f}[/bold]\n")

    def print_scaling_summary(self, all_summaries: list):
        self.console.rule("[bold magenta]Scaling Evaluation Results (Document Level)[/bold magenta]")
        table = self._build_rich_table(all_summaries, is_scaling=True)
        self.console.print(table)

    @staticmethod
    def _build_rich_table(data, is_scaling=False) -> Table:
        # Internal helper for Rich terminal tables
        table = Table(show_header=True, header_style="bold cyan", expand=True)
        ks = [1, 3, 5, 10]
        
        if is_scaling:
            table.add_column("Samples")
            summaries = data
            available_metrics = summaries[0].get("available_metrics", ["recall"])
            for metric in available_metrics:
                for k in ks:
                    table.add_column(f"{metric.title()}@{k}", justify="right")
            for s in summaries:
                row = [str(s["num_samples"])]
                for metric in available_metrics:
                    for k in ks:
                        row.append(f"{s.get(f'{metric}@{k}', 0):.3f}")
                table.add_row(*row)
        else:
            summary = data
            table.add_column("Metric")
            for k in ks:
                table.add_column(f"@{k}", justify="right")
            available_metrics = summary.get("available_metrics", [])
            for metric in available_metrics:
                row = [metric.upper()]
                for k in ks:
                    row.append(f"{summary.get(f'{metric}@{k}', 0):.3f}")
                table.add_row(*row)
        return table

    def generate_markdown_report(self, 
                                 summary_data: Any,
                                 tracker_report: str, 
                                 is_scaling: bool = True,
                                 plot_filename: str = None) -> str:
        """Generates a clean Markdown report without any ANSI codes or truncation."""
        md = []
        ks = [1, 3, 5, 10]

        if is_scaling:
            md.append("# Scaling Evaluation Results (Document Level)")
            summaries = summary_data
            available_metrics = summaries[0].get("available_metrics", ["recall"])

            # Header
            header = ["Samples"]
            for m in available_metrics:
                for k in ks:
                    header.append(f"{m.title()}@{k}")
            header.append("Global Recall")

            md.append("| " + " | ".join(header) + " |")
            md.append("| " + " | ".join(["---"] * len(header)) + " |")

            # Rows
            for s in summaries:
                row = [str(s["num_samples"])]
                for m in available_metrics:
                    for k in ks:
                        val = s.get(f"{m}@{k}", 0)
                        row.append(f"{val:.3f}")
                row.append(f"{s.get('global_recall', 0):.3f}")
                md.append("| " + " | ".join(row) + " |")

            # Error Analysis from last step
            last_summary = summaries[-1]
            md.append(self._generate_failed_queries_markdown(last_summary))
        else:
            md.append("# Evaluation Summary (Document Level)")
            md.append(self._generate_failed_queries_markdown(summary_data))

        # Add Plot if available
        if plot_filename:
            md.append("\n## Visual Analysis: Metrics Scaling")
            md.append(f"![Scaling Performance Plot]({plot_filename})")

        md.append("\n## Pipeline Performance Report (Timings)")
        md.append("```text")
        md.append(tracker_report.strip())
        md.append("```")

        return "\n".join(md)


    @staticmethod
    def _generate_failed_queries_markdown(summary: dict) -> str:
        failures = summary.get("failed_queries_sample", [])
        if not failures:
            return ""

        md = ["\n## Sample Retrieval Failures (Error Analysis)",
              "| Question | Expected IDs (Target) | Top Retrieved (Mistake) |", "| --- | --- | --- |"]

        for f in failures:
            expected = ", ".join(f["expected_ids"]) if isinstance(f["expected_ids"], list) else f["expected_ids"]
            # Clean Markdown table special chars
            q = f["question"].replace("|", "\\|")
            mistake = f["top_mistake"].replace("|", "\\|")
            md.append(f"| {q} | {expected} | {mistake} |")
        
        return "\n".join(md)

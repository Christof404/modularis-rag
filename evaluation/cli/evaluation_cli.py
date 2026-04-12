from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from ..core.discovery import ComponentInspector
from ..core.reporting import ResultPresenter
from ..pipeline import EvaluationPipeline
from rich.console import Console
from ..registry import REGISTRY
from rich.panel import Panel
import questionary
import pathlib
import inspect
import os


class EvaluationCLI:
    def __init__(self):
        self.console = Console()
        self.pipeline = EvaluationPipeline()
        self.presenter = ResultPresenter(self.console)
        self.inspector = ComponentInspector()
        self.cur_dir = pathlib.Path(__file__).parent.parent.absolute()

    def _ask_component_params(self, component, prefilled_kwargs: dict) -> dict:
        """
        Interactively asks for component parameters using DiscoveryService metadata.
        """
        component_params = self.inspector.get_component_params(component)
        
        # Initialize with prefilled_kwargs that are accepted by the component
        sig = inspect.signature(component)
        param_dict = {k: v for k, v in prefilled_kwargs.items() if k in sig.parameters}

        for param_name, param_info in component_params.items():
            if param_name in param_dict:
                continue

            param_type = param_info["type"]
            param_default = param_info["default"]
            has_default = param_info["has_default"]

            default_prompt_val = str(param_default) if has_default and param_default is not None else ""
            type_str = getattr(param_type, '__name__', str(param_type)).replace('typing.', '')
            
            value_str = questionary.text(f"Enter value for '{param_name}' [{type_str}]:",
                                         default=default_prompt_val).ask()
            
            if value_str is None:
                raise KeyboardInterrupt

            value_str = value_str.strip()
            if not value_str:
                param_dict[param_name] = param_default if has_default else None
                continue

            # Basic type conversion
            if 'int' in str(param_type).lower():
                try:
                    param_dict[param_name] = int(value_str)
                except ValueError:
                    self.console.print(f"[yellow][Warning]: '{value_str}' is not an int. Using Default.[/yellow]")
                    param_dict[param_name] = param_default if has_default else None
            elif 'float' in str(param_type).lower():
                try:
                    param_dict[param_name] = float(value_str)
                except ValueError:
                    self.console.print(f"[yellow][Warning]: '{value_str}' is not a float. Using Default.[/yellow]")
                    param_dict[param_name] = param_default if has_default else None
            else:
                param_dict[param_name] = value_str

        return param_dict

    def run(self):
        self.console.print(Panel.fit("[bold cyan]RAG Pipeline Evaluation[/bold cyan]", border_style="cyan"))

        # 1. Source selection (dataset)
        eval_source_key = questionary.select("Select evaluation source (dataset):",
                                             choices=list(REGISTRY["sources"].keys())).ask()
        
        if not eval_source_key:
            return

        # 2. RetrievalPipeline selection
        default_config = os.path.join(self.cur_dir, "pipeline_config.json")
        pipeline_config_path = questionary.path("Select retrieval pipeline config:",
                                                default=default_config).ask()

        if not pipeline_config_path:
            self.console.print("[bold red]No retrieval config provided, abort.[/bold red]")
            return

        # 3. Sample specifications
        start_val = int(questionary.text("Start num_test_samples:", default="50").ask() or 50)
        end_val = int(questionary.text("End num_test_samples:", default="200").ask() or 200)
        step_val = int(questionary.text("Step size:", default="50").ask() or 50)

        # 4. Metric selection
        choices = [questionary.Choice(title=m, value=m, checked=True) for m in REGISTRY["metrics"].keys()]
        selected_metrics_keys = questionary.checkbox("Select metrics to evaluate:",
                                                     choices=choices).ask()

        if selected_metrics_keys is None:
            selected_metrics_keys = list(REGISTRY["metrics"].keys())

        # Instantiate basic components
        retrieval_pipeline = self.pipeline.load_retrieval_pipeline(pipeline_config_path)
        metrics = [REGISTRY["metrics"][k]() for k in selected_metrics_keys]

        use_only_req = questionary.confirm("Use only required docs (limit DB size to match current samples)?",
                                           default=True).ask()

        # Gather parameters for the source
        prefilled_kwargs = {"retrieval_pipeline": retrieval_pipeline,
                            "metrics": metrics,
                            "use_only_required_docs": use_only_req}
        
        source_class = REGISTRY["sources"][eval_source_key]
        base_parameters = self._ask_component_params(source_class, prefilled_kwargs=prefilled_kwargs)

        # 5. Run evaluation(s)
        steps = list(range(start_val, end_val + 1, step_val))
        total_questions = max(steps)

        self.console.print(f"\n[bold yellow]Starting evaluation scaling for {eval_source_key}...[/bold yellow]")

        with Progress(SpinnerColumn(),
                      TextColumn("[progress.description]{task.description}"),
                      BarColumn(),
                      TaskProgressColumn(),
                      TimeRemainingColumn(),
                      console=self.console) as progress:
            
            global_task = progress.add_task("[cyan]Overall Evaluation Progress", total=total_questions)
            
            def update_progress():
                progress.advance(global_task)

            # Use the new pipeline service method
            all_summaries = self.pipeline.run_scaling(evaluation_source=eval_source_key,
                                                      base_parameters=base_parameters,
                                                      steps=steps,
                                                      progress_callback=update_progress)

        # 6. Present Results
        if len(all_summaries) > 1:
            self.presenter.print_scaling_summary(all_summaries)
        else:
            self.presenter.print_evaluation_summary(all_summaries[0])
        
        self.pipeline.print_tracker_report()

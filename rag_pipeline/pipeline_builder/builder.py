from ..core.base_interfaces import BasePipeline, PipelineComponent, BaseRegistry
from ..core.models import Pipeline, PipelineStep
from ..core.factory import Factory
from rich.console import Console
from rich.rule import Rule
from typing import Type
import questionary
import inspect
import typing
import json
import ast



class UseDefault:
    """Internal marker to indicate that the default value should be used and NOT stored in the config."""
    pass


class PipelineBuilder:
    def __init__(self, pipeline_save_path: str, pipeline: Type[BasePipeline], registry: BaseRegistry):
        self.pipeline = pipeline
        self.registry = registry
        self.console = Console()
        self.factory = Factory(self.registry, pipeline_save_path)

    def _build(self):
        final_config = {}

        # show Pipeline to build
        self.pipeline.show()

        # 1. get pipeline structure
        pipeline_structure = self.pipeline.get_build_info()

        # 2. ask for all components in correct order given by pipeline_structure#
        step_counter = 1
        for label, component_type in pipeline_structure:
            component_type, is_optional = self.pipeline.unwrap_optional(component_type)

            origin = typing.get_origin(component_type)
            args = typing.get_args(component_type)

            rule_name = label
            if origin in (list, typing.List):
                inner_type = args[0] if args else None
                inner_type, _ = self.pipeline.unwrap_optional(inner_type)

                if inner_type and hasattr(inner_type, "__name__"):
                    type_hint = f" ({inner_type.__name__.replace('Base', '')}(s))"
                else:
                    type_hint = ""
            elif isinstance(component_type, type):
                type_hint = f" ({component_type.__name__.replace('Base', '')})"
            else:
                type_hint = ""

            self.console.print(Rule(f"Step {step_counter}: {rule_name}{type_hint}", style="bold cyan"))
            step_counter += 1

            if is_optional:
                use_it = questionary.confirm(f"Add optional {rule_name}?").ask()
                if not use_it:
                    continue

            if origin in (list, typing.List):
                inner_type = args[0] if args else None
                inner_type, _ = self.pipeline.unwrap_optional(inner_type)

                if inner_type and isinstance(inner_type, type) and issubclass(inner_type, PipelineComponent):
                    final_config[label] = self._ask_component_list(inner_type,
                                                                   label,
                                                                   indent_level=0)

            elif isinstance(component_type, type) and issubclass(component_type, PipelineComponent):
                final_config[label] = self._ask_component(component_type, indent_level=0)

        return final_config

    def _ask_component(self, component: Type[PipelineComponent], indent_level: int = 0):
        indent = " " * indent_level
        # 1. show available
        selected_component = questionary.select(f"{indent}Select {component.__name__}:",
                                                choices=self.registry.get_available(component._type)).ask()

        # 2. ask for parameters
        selected_component = self.registry.get_component_class(selected_component)

        param_dict = self._ask_component_params(selected_component, indent_level=indent_level)
        return {"component_name": selected_component.name,
                "params": param_dict}

    def _ask_component_params(self, component: Type[PipelineComponent], indent_level: int = 0) -> dict:
        component_params = self._get_params(component)
        param_dict = {}

        for param_name, param_info in component_params.items():
            raw_type = param_info["type"]
            param_default = param_info["default"]

            param_type, is_optional = self.pipeline.unwrap_optional(raw_type)
            origin_type = typing.get_origin(param_type)
            args = typing.get_args(param_type)

            # Optional[List[Component]] or List[Component]
            if origin_type in (list, typing.List):
                inner_type = args[0] if args else None
                inner_type, _ = self.pipeline.unwrap_optional(inner_type)

                if inner_type and isinstance(inner_type, type) and issubclass(inner_type, PipelineComponent):
                    if is_optional:
                        use_it = questionary.confirm(f"Configure optional list '{param_name}'?").ask()
                        if not use_it:
                            param_dict[param_name] = None
                            continue

                    param_dict[param_name] = self._ask_component_list(inner_type,
                                                                      param_name,
                                                                      indent_level=indent_level + 2)
                else:
                    val = self._ask_primitive(param_name,
                                               param_type,
                                               param_default,
                                               indent_level=indent_level + 2)
                    if not isinstance(val, UseDefault):
                        param_dict[param_name] = val

            # Optional[Component] or Component
            elif isinstance(param_type, type) and issubclass(param_type, PipelineComponent):
                if is_optional:
                    use_it = questionary.confirm(f"Configure optional component '{param_name}'?").ask()
                    if not use_it:
                        param_dict[param_name] = None
                        continue

                self.console.print(f"\n{indent_level * ' '}[dim]── Sub-Component: {param_name} ──[/dim]")
                param_dict[param_name] = self._ask_component(param_type, indent_level=indent_level + 2)

            # Primitive
            else:
                val = self._ask_primitive(param_name,
                                           param_type,
                                           param_default,
                                           indent_level=indent_level + 2)
                if not isinstance(val, UseDefault):
                    param_dict[param_name] = val

        return param_dict

    def _ask_component_list(self, component_base_class: Type[PipelineComponent], param_name: str, indent_level: int = 0) -> list:
        indent = " " * indent_level
        self.console.print(f"\n{indent}[dim]─── Nested List: {param_name} ───[/dim]")
        components = []
        while True:
            add_more = questionary.confirm(f"{indent}Add a {component_base_class.__name__}?").ask()

            if not add_more:
                break

            config = self._ask_component(component_base_class)
            if config:
                components.append(config)
        self.console.print(f"{indent}[dim]──────────────────────────────[/dim]\n")
        return components

    def _ask_primitive(self, name: str, param_type: type, param_default: typing.Any, indent_level: int) -> typing.Any:
        indent = " " * indent_level
        clean_type = self._clean_type_name(param_type)
        default_text = "" if param_default == inspect._empty else f" (default: {param_default})"

        self.console.print(f"{indent}{clean_type:<10} {name}{default_text}")
        value = input(f"{indent}-> ")

        if not value.strip() and param_default != inspect._empty:
            # handle Path objects
            if hasattr(param_default, "resolve"):
                return str(param_default)

            # Check if serializable
            try:
                json.dumps(param_default)
            except (TypeError, OverflowError):
                return UseDefault()

            return param_default

        # cast string values to correct type
        try:
            # Handle Union/Optional types
            param_type, _ = self.pipeline.unwrap_optional(param_type)
            origin = typing.get_origin(param_type)

            if param_type is bool:
                return value.lower() in ['true', '1', 'yes', 'y']
            elif param_type is int:
                return int(value)
            elif param_type is float:
                return float(value)
            elif str(param_type) == "<class 'pathlib.Path'>" or (
                    hasattr(param_type, '__name__') and param_type.__name__ == 'Path'):
                return str(value)

            # handle list types
            if origin in (list, typing.List):
                try:
                    eval_value = ast.literal_eval(value)
                    if isinstance(eval_value, list):
                        return eval_value
                except (ValueError, SyntaxError):
                    pass

        except ValueError:
            self.console.print(f"{indent}[red]Warning: Could not cast {value} to {clean_type}. Use String.[/red]")

        return value

    @staticmethod
    def _clean_type_name(param_type: type) -> str:
        if param_type == inspect._empty:
            return "[any]"

        if hasattr(param_type, "__name__"):
            return f"[{param_type.__name__}]"

        type_str = str(param_type).replace("typing.", "")
        if type_str.startswith("Literal"):
            return "[Literal]"
        if type_str.startswith("List"):
            return "[List]"

        return f"[{type_str}]"

    @staticmethod
    def _get_params(component) -> dict:
        sig = inspect.signature(component)
        param_dict = {}
        for name, param in sig.parameters.items():
            if param.kind == inspect.Parameter.VAR_KEYWORD or param.kind == inspect.Parameter.VAR_POSITIONAL:
                continue
            param_dict[name] = {"type": param.annotation, "default": param.default}

        return param_dict

    @staticmethod
    def _create_pipeline_object(config_dict: dict) -> Pipeline:
        pipeline = Pipeline()

        def _extract_steps(key: str, value: typing.Any, parent_name: str = None):
            if not value:
                return

            comp_type = key.replace("Base", "").replace("_list", "").capitalize()
            if parent_name:
                comp_type = f"{comp_type} (Sub)"

            if isinstance(value, list):
                for item in value:
                    _extract_steps(key, item, parent_name)

            elif isinstance(value, dict) and "component_name" in value:
                comp_name = value["component_name"]
                desc = f"Inside {parent_name}" if parent_name else None

                pipeline.append(PipelineStep(component_type=comp_type,
                                             component_name=comp_name,
                                             description=desc))

                for param_key, param_value in value.get("params", {}).items():
                    if isinstance(param_value, dict) and "component_name" in param_value:
                        _extract_steps(param_key, param_value, parent_name=comp_name)
                    elif isinstance(param_value, list) and param_value and isinstance(param_value[0], dict) and "component_name" in param_value[0]:
                        _extract_steps(param_key, param_value, parent_name=comp_name)

        for top_key, top_val in config_dict.items():
            _extract_steps(top_key, top_val)

        return pipeline


    def build(self):
        # 1. build config
        config = self._build()

        # 2. show config summary
        self.console.print("\n")
        self.console.print(Rule("Configuration Summary", style="bold green"))
        summary_pipeline = self._create_pipeline_object(config)
        self.console.print(summary_pipeline)

        # 3. Save config
        self.factory.save_pipeline_config(config)

        return config

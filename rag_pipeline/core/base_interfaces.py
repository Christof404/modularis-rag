from .models import Chunk, EmbeddedChunk, Pipeline, PipelineStep, EmbeddingModel
from typing import List, Type, Dict, Any, Tuple, Union
from abc import ABC, abstractmethod
from rich.console import Console
from rich.table import Table
import typing
import types


class PipelineComponent(ABC):
    """
    Base class for all pipeline components with automatic type/name detection.
    """

    def __init__(self, **kwargs):
        pass

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Automatically derive type from class name (example: "BaseSource" -> "Source")
        if not hasattr(cls, '_type'):
            cls._type = cls.__name__.replace("Base", "")

        if 'name' not in cls.__dict__:
            cls.name = cls.__name__  # take correct name

    def get_identifier(self) -> dict:
        return {"type": self._type, "name": self.name}

    @property
    def metadata_description(self) -> Any:
        return None

class BasePipeline(ABC):
    """
    Base-Interface for all  Pipelines (Ingest, Retrieval, etc.)
    """
    @abstractmethod
    def run(self, *args, **kwargs):
        """
        start the pipeline
        """
        pass

    @staticmethod
    @abstractmethod
    def get_build_info() -> List[Tuple[str, Any]]:
        """
        return build information for pipeline builder (name/key, type)
        """
        pass

    @staticmethod
    def unwrap_optional(tp):
        origin = typing.get_origin(tp)
        if origin in (Union, types.UnionType):
            args = [arg for arg in typing.get_args(tp) if arg is not type(None)]
            if len(args) == 1:
                return args[0], True
        return tp, False

    @classmethod
    def print_build_config(cls):
        """Prints the Build Config table for the pipeline class."""
        pipeline_structure = cls.get_build_info()
        console = Console()

        table = Table(title=f"Configuration Steps for [bold green]{cls.__name__}[/bold green]",
                      show_header=True,
                      header_style="bold cyan")

        table.add_column("Step", style="dim", justify="right", width=4)
        table.add_column("Parameter Name", style="blue")
        table.add_column("Expected Component", style="magenta")
        table.add_column("Multiplicity", style="yellow")

        for i, (label, component_type) in enumerate(pipeline_structure, 1):
            component_type, is_optional = cls.unwrap_optional(component_type)

            origin = typing.get_origin(component_type)
            args = typing.get_args(component_type)

            comp_name = "Unknown"
            multiplicity = "Optional Single" if is_optional else "Single"

            if origin in (list, typing.List):
                inner_type = args[0] if args else None
                inner_type, _ = cls.unwrap_optional(inner_type)

                if inner_type and hasattr(inner_type, "__name__"):
                    comp_name = inner_type.__name__.replace("Base", "") + "(s)"
                    multiplicity = "Optional Multiple (List)" if is_optional else "Multiple (List)"
                else:
                    comp_name = str(component_type)

            elif isinstance(component_type, type):
                comp_name = component_type.__name__.replace("Base", "")
                multiplicity = "Optional Single" if is_optional else "Single"

            table.add_row(str(i), label, comp_name, multiplicity)

        console.print(table)
        console.print("\n")

    def get_pipeline_model(self) -> Pipeline:
        """
        Generates a Pipeline model by inspecting the instance based on get_build_info.
        """
        p = Pipeline()
        build_info = self.get_build_info()

        def _add_component(comp, prefix="", is_last=True, is_root=False):
            if not comp:
                return

            display_prefix = ""
            if not is_root:
                display_prefix = prefix + ("└── " if is_last else "├── ")

            comp_type = f"{display_prefix}{comp.get_identifier().get('type')}"
            desc = getattr(comp, 'metadata_description', None)

            p.append(PipelineStep(component_type=comp_type,
                                  component_name=comp.name,
                                  description=desc))

            child_prefix = prefix
            if not is_root:
                child_prefix += "    " if is_last else "│   "

            children = []
            filters = getattr(comp, 'filters', None)
            if isinstance(filters, list):
                children.extend(filters)

            extractors = getattr(comp, 'extractors', None)
            if isinstance(extractors, list):
                children.extend(extractors)

            for _i, child in enumerate(children):
                if isinstance(child, PipelineComponent):
                    _add_component(child, child_prefix, is_last=(_i == len(children) - 1))

        for label, _ in build_info:
            attr = getattr(self, label, None)
            if not attr:
                continue

            if isinstance(attr, list):
                for item in attr:
                    if isinstance(item, PipelineComponent):
                        _add_component(item, is_root=True)
            elif isinstance(attr, PipelineComponent):
                _add_component(attr, is_root=True)

        return p

    def print_pipeline(self):
        """
        Prints the pipeline. If called on an instance, it prints the workflow.
        """
        console = Console()
        console.print(self.get_pipeline_model())

    @classmethod
    def show(cls):
        cls.print_build_config()


class BaseEmbedder(PipelineComponent):
    """
    Responsible for vectorizing text chunks.
    """

    @abstractmethod
    def get_model(self) -> EmbeddingModel:
        pass

    @abstractmethod
    def get_prefix(self) -> str:
        pass

    @abstractmethod
    def embed(self, chunks: List[Chunk]) -> List[EmbeddedChunk]:
        """
        Takes a list of chunks without embeds, creates an embed for each chunk, and adds it

        :return List[Chunk] with embedded chunks
        """
        pass


class BaseRegistry(ABC):
    @abstractmethod
    def get_component_class(self, comp_name: str) -> Type[PipelineComponent]:
        pass

    @abstractmethod
    def get_available(self, category: str) -> Dict[str, Type[PipelineComponent]]:
        pass


class BaseFactory(ABC):
    @abstractmethod
    def save_pipeline_config(self, config_dict: dict) -> None:
        pass
    @abstractmethod
    def instantiate_from_config(self, config_node: Any) -> Any:
        pass

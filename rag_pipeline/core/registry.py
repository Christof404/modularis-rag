from .base_interfaces import BaseRegistry, PipelineComponent
from typing import Type, Dict

class ComponentRegistry(BaseRegistry):
    def __init__(self, registry_dict: Dict[str, Dict[str, Type[PipelineComponent]]]):
        self.registry_dict = registry_dict

    def get_component_class(self, comp_name: str) -> Type[PipelineComponent]:
        """
        Searches for a component class by name in all registry categories.
        """
        for category in self.registry_dict.values():
            if comp_name in category:
                return category[comp_name]

        raise TypeError(f"{comp_name} is not a registered component type")

    def get_available(self, category: str) -> Dict[str, Type[PipelineComponent]]:
        """
        Searches for a category by name and return all components from this category.
        """
        category = category.lower()
        return self.registry_dict[category]

from .base_interfaces import BaseRegistry, BaseFactory
from typing import Any
import json


class Factory(BaseFactory):
    def __init__(self, registry: BaseRegistry, config_save_path: str = "pipeline_config.json"):
        self.config_save_path = config_save_path
        self.registry = registry

    def save_pipeline_config(self, config_dict: dict) -> None:
        with open(self.config_save_path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4)
        print(f"\nPipeline-Configuration saved in: {self.config_save_path}")


    def instantiate_from_config(self, config_node: Any) -> Any:
        # Case 1: It is a list (e.g., multiple filters)
        if isinstance(config_node, list):
            return [self.instantiate_from_config(item) for item in config_node]

        # 2. Case: It is a dictionary
        if isinstance(config_node, dict):
            if "component_name" in config_node:
                cls = self.registry.get_component_class(config_node["component_name"])

                # recursive build all filters
                params = {k: self.instantiate_from_config(v) for k, v in config_node.get("params", {}).items()}

                # Instantiate the class with the parameters!
                return cls(**params)

            # Just normal dict
            return {k: self.instantiate_from_config(v) for k, v in config_node.items()}

        # Case 3: Primitive value (int, bool, str)
        return config_node

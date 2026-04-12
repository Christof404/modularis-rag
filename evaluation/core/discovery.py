import inspect

class ComponentInspector:
    """
    Service to inspect evaluation components and their required parameters.
    """
    
    @staticmethod
    def get_component_params(component) -> dict:
        """
        Analyzes the signature of a component (Source or Metric) and returns metadata.
        """
        sig = inspect.signature(component)
        param_dict = {}
        
        # Parameters that are handled automatically or internally
        internal_params = ["retrieval_pipeline",
                           "metrics",
                           "num_test_samples",
                           "use_only_required_docs",
                           "questions"]
        
        for name, param in sig.parameters.items():
            if param.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
                continue
            if name in internal_params:
                continue
                
            param_dict[name] = {"type": param.annotation,
                                "default": param.default,
                                "has_default": param.default is not inspect.Parameter.empty}
        return param_dict

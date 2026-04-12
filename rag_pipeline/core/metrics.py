from contextlib import contextmanager
from abc import ABC, abstractmethod
from collections import defaultdict
import time


class BasePerformanceTracker(ABC):
    @abstractmethod
    @contextmanager
    def measure(self, component_type: str, component_name: str):
        pass

    @abstractmethod
    def get_report(self) -> str:
        pass

class NullTracker(BasePerformanceTracker):
    @contextmanager
    def measure(self, component_type: str, component_name: str):
        yield

    def get_report(self) -> str:
        return "NullTracker: No performance metrics tracked."

    def print_report(self):
        print(self.get_report())

class PipelineTracker(BasePerformanceTracker):
    def __init__(self):
        self.timings = defaultdict(lambda: defaultdict(float))
        self.calls = defaultdict(lambda: defaultdict(int))

    @contextmanager
    def measure(self, component_type: str, component_name: str):
        start_time = time.perf_counter()
        try:
            yield  # this is where the actual pipeline code runs.
        finally:
            duration = time.perf_counter() - start_time
            self.timings[component_type][component_name] += duration
            self.calls[component_type][component_name] += 1

    def get_report(self) -> str:
        report = ["\n" + "=" * 50, "PIPELINE PERFORMANCE REPORT", "=" * 50]
        for comp_type, components in self.timings.items():
            report.append(f"\n[{comp_type}]")
            for name, duration in components.items():
                calls = self.calls[comp_type][name]
                avg = (duration / calls) * 1000 if calls > 0 else 0
                report.append(f"  {name}: {duration:.2f}s total | {calls} calls | ~{avg:.2f}ms/call")
        report.append("="*50 + "\n")
        return "\n".join(report)

    def print_report(self):
        print(self.get_report())

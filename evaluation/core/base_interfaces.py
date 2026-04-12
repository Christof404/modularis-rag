from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Tuple

class Metric(BaseModel):
    k: int
    result: float

class BasePerformanceMetric(ABC):
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__.lower()

    @abstractmethod
    def evaluate(self, retrieved: Tuple[str, ...], expected: Tuple[str, ...], at_k: List[int]) -> List[Metric]:
        pass

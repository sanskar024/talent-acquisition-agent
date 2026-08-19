from abc import ABC, abstractmethod
from typing import Any, Dict
import logging


class BaseAgent(ABC):
    """
    Every agent implements `run(**kwargs) -> dict` and logs a structured
    trace entry so the orchestrator can build an auditable step-by-step
    record of the decision — important for both debugging and the
    explainability side of the bias-mitigation story.
    """

    name: str = "base_agent"

    def __init__(self):
        self.logger = logging.getLogger(f"talentflow.agents.{self.name}")

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        ...

    def trace(self, **details) -> Dict[str, Any]:
        entry = {"agent": self.name, **details}
        self.logger.info("%s", entry)
        return entry

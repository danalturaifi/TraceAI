"""
Base class for all TraceAI analysis agents.
Each agent receives transaction/client data and returns a structured finding.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import logging

logger = logging.getLogger("traceai.agents")

@dataclass
class AgentFinding:
    agent_name: str
    triggered: bool
    score: float          # 0.0 – 1.0
    severity: str         # low / medium / high / critical
    pattern_type: str
    explanation: str      # human-readable XAI output
    shap_contributions: dict[str, float] = field(default_factory=dict)
    recommended_action: str = ""
    evidence: list[str] = field(default_factory=list)

    @property
    def risk_label(self) -> str:
        if self.score >= 0.90: return "critical"
        if self.score >= 0.75: return "high"
        if self.score >= 0.45: return "medium"
        return "low"

class BaseAgent(ABC):
    name: str = "base"
    version: str = "1.0"

    def run(self, context: dict[str, Any]) -> AgentFinding:
        try:
            return self._analyze(context)
        except Exception as e:
            logger.error(f"Agent {self.name} failed: {e}", exc_info=True)
            return AgentFinding(
                agent_name=self.name,
                triggered=False,
                score=0.0,
                severity="low",
                pattern_type="error",
                explanation=f"Agent error: {str(e)}",
            )

    @abstractmethod
    def _analyze(self, context: dict[str, Any]) -> AgentFinding:
        ...

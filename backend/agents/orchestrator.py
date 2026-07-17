"""
Agent Orchestrator
Runs all detection agents in parallel, aggregates scores,
produces a unified risk assessment with XAI explanation.
This is what the API calls for every transaction analysis.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from dataclasses import dataclass, field

from agents.base_agent import AgentFinding
from agents.structuring_agent import StructuringAgent
from agents.shell_company_agent import ShellCompanyAgent
from agents.layering_agent import LayeringAgent
from agents.pep_agent import PEPAgent
from agents.behavioral_agent import BehavioralAgent

# Agent weights — tuned for SAMA AML priorities
AGENT_WEIGHTS = {
    "StructuringAgent":  0.25,
    "ShellCompanyAgent": 0.25,
    "LayeringAgent":     0.20,
    "PEPAgent":          0.20,
    "BehavioralAgent":   0.10,
}

AGENTS = [
    StructuringAgent(),
    ShellCompanyAgent(),
    LayeringAgent(),
    PEPAgent(),
    BehavioralAgent(),
]

@dataclass
class OrchestratorResult:
    composite_score: float
    severity: str
    triggered_agents: list[AgentFinding]
    all_findings: list[AgentFinding]
    top_pattern: str
    unified_explanation: str
    recommended_action: str
    shap_summary: dict[str, float] = field(default_factory=dict)

    @property
    def should_block(self) -> bool:
        return (
            self.composite_score >= 0.90
            or any(f.score >= 0.95 and f.triggered for f in self.triggered_agents)
        )

    @property
    def should_file_str(self) -> bool:
        return self.composite_score >= 0.75

    @property
    def should_edd(self) -> bool:
        return self.composite_score >= 0.50


def _run_agent(agent, context: dict[str, Any]) -> AgentFinding:
    return agent.run(context)


def analyze_transaction(context: dict[str, Any]) -> OrchestratorResult:
    """
    Run all agents synchronously (use in background tasks / notebooks).
    """
    with ThreadPoolExecutor(max_workers=len(AGENTS)) as ex:
        futures  = {ex.submit(_run_agent, agent, context): agent for agent in AGENTS}
        findings = [f.result() for f in futures]

    return _aggregate(findings)


async def analyze_transaction_async(context: dict[str, Any]) -> OrchestratorResult:
    """
    Async wrapper for use inside FastAPI route handlers.
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=len(AGENTS)) as ex:
        tasks    = [loop.run_in_executor(ex, _run_agent, agent, context) for agent in AGENTS]
        findings = await asyncio.gather(*tasks)

    return _aggregate(list(findings))


def _aggregate(findings: list[AgentFinding]) -> OrchestratorResult:
    triggered = [f for f in findings if f.triggered]

    # Weighted composite score
    composite = sum(
        f.score * AGENT_WEIGHTS.get(f.agent_name, 0.10)
        for f in findings
    )
    # Boost if multiple agents triggered simultaneously
    if len(triggered) >= 3:
        composite = min(composite * 1.15, 1.0)

    composite = round(composite, 3)

    severity = ("critical" if composite >= 0.90 else
                "high"     if composite >= 0.75 else
                "medium"   if composite >= 0.45 else "low")

    # Top pattern = highest-scoring triggered agent
    top_finding = max(triggered, key=lambda f: f.score) if triggered else None
    top_pattern = top_finding.pattern_type if top_finding else "None"

    # Unified SHAP: flatten all agent SHAP values
    shap_summary: dict[str, float] = {}
    for f in findings:
        for k, v in f.shap_contributions.items():
            shap_summary[k] = shap_summary.get(k, 0) + v

    # Recommended action — take most severe recommendation
    action_priority = [
        "Block transaction + File STR immediately",
        "Block + Escalate to CCO + File STR",
        "Mandatory EDD + CCO approval required before processing",
        "Initiate EDD + File STR",
        "Initiate EDD + Request UBO documentation",
        "Flag for senior analyst review",
        "Flag for manual review",
        "Enhanced scrutiny + document source of funds",
        "Flag for senior review + Request transaction justification",
        "Clear",
    ]
    recommended = "Clear"
    for action in action_priority:
        if any(f.recommended_action == action for f in triggered):
            recommended = action
            break

    # Unified explanation
    if triggered:
        parts = [f"[{f.pattern_type}] {f.explanation}" for f in triggered]
        unified = (
            f"AI analysis complete — {len(triggered)} pattern(s) detected. "
            f"Composite risk score: {composite:.2f} ({severity.upper()}). "
            + " || ".join(parts)
        )
    else:
        unified = f"No suspicious patterns detected. Composite score: {composite:.2f}."

    return OrchestratorResult(
        composite_score=composite,
        severity=severity,
        triggered_agents=triggered,
        all_findings=findings,
        top_pattern=top_pattern,
        unified_explanation=unified,
        recommended_action=recommended,
        shap_summary={k: round(v, 3) for k, v in shap_summary.items()},
    )

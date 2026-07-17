"""
/api/analysis — AI agent analysis endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from middleware.auth import require_reviewer
from agents.orchestrator import analyze_transaction_async, OrchestratorResult

router = APIRouter(prefix="/api/analysis", tags=["AI Analysis"])


class AnalysisRequest(BaseModel):
    transaction: dict
    client: dict
    client_history: list[dict] = []
    client_avg_amount: float = 0
    has_commercial_invoice: bool = False
    third_party_payor: bool = False


class AnalysisResponse(BaseModel):
    composite_score: float
    severity: str
    top_pattern: str
    recommended_action: str
    should_block: bool
    should_file_str: bool
    should_edd: bool
    triggered_patterns: list[str]
    unified_explanation: str
    shap_summary: dict[str, float]
    agent_findings: list[dict]


@router.post("/transaction", response_model=AnalysisResponse)
async def analyze(
    body: AnalysisRequest,
    user: dict = Depends(require_reviewer),
):
    # Convert datetime strings to datetime objects for agents
    context = body.model_dump()
    if context["transaction"].get("datetime"):
        try:
            context["transaction"]["datetime"] = datetime.fromisoformat(
                context["transaction"]["datetime"]
            )
        except (ValueError, TypeError):
            pass

    for hist_txn in context.get("client_history", []):
        if hist_txn.get("datetime"):
            try:
                hist_txn["datetime"] = datetime.fromisoformat(hist_txn["datetime"])
            except (ValueError, TypeError):
                pass

    result: OrchestratorResult = await analyze_transaction_async(context)

    return AnalysisResponse(
        composite_score    =result.composite_score,
        severity           =result.severity,
        top_pattern        =result.top_pattern,
        recommended_action =result.recommended_action,
        should_block       =result.should_block,
        should_file_str    =result.should_file_str,
        should_edd         =result.should_edd,
        triggered_patterns =[f.pattern_type for f in result.triggered_agents],
        unified_explanation=result.unified_explanation,
        shap_summary       =result.shap_summary,
        agent_findings     =[
            {
                "agent":      f.agent_name,
                "triggered":  f.triggered,
                "score":      f.score,
                "severity":   f.severity,
                "pattern":    f.pattern_type,
                "explanation":f.explanation,
                "action":     f.recommended_action,
                "evidence":   f.evidence,
                "shap":       f.shap_contributions,
            }
            for f in result.all_findings
        ],
    )

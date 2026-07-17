"""
Structuring / Smurfing Detection Agent
Detects deliberate splitting of transactions to stay below reporting thresholds.
FATF Typology: Structuring (SAMA AML Article 6)
"""
from agents.base_agent import BaseAgent, AgentFinding
from typing import Any

THRESHOLD_SAR = 1_000_000   # SAMA reporting threshold
WINDOW_DAYS   = 30
MIN_PATTERN   = 3           # minimum occurrences to flag


class StructuringAgent(BaseAgent):
    name = "StructuringAgent"
    version = "1.1"

    def _analyze(self, context: dict[str, Any]) -> AgentFinding:
        txn        = context["transaction"]
        history    = context.get("client_history", [])  # list of recent txns

        amount     = txn["amount"]
        client_avg = context.get("client_avg_amount", amount)

        # Collect recent sub-threshold transactions from same client
        recent_sub = [
            t for t in history
            if t["amount"] < THRESHOLD_SAR
            and t["amount"] > THRESHOLD_SAR * 0.7   # in the suspicious zone
        ]

        # Feature engineering
        count_sub      = len(recent_sub)
        total_sub      = sum(t["amount"] for t in recent_sub) + amount
        vol_spike      = amount / max(client_avg, 1)
        below_by_pct   = (THRESHOLD_SAR - amount) / THRESHOLD_SAR if amount < THRESHOLD_SAR else 0

        # Score components (each 0–1, weighted)
        score_count    = min(count_sub / MIN_PATTERN, 1.0) * 0.40
        score_spike    = min(vol_spike / 5, 1.0)           * 0.25
        score_proximity= below_by_pct                      * 0.25  # closer to threshold = more suspicious
        score_total    = min(total_sub / (THRESHOLD_SAR * 3), 1.0) * 0.10

        composite = score_count + score_spike + score_proximity + score_total

        # SHAP-style contributions (simplified feature attribution)
        shap = {
            "sub_threshold_count":    round(score_count, 3),
            "volume_spike_ratio":     round(score_spike, 3),
            "proximity_to_threshold": round(score_proximity, 3),
            "cumulative_total":       round(score_total, 3),
        }

        triggered = composite >= 0.45 or count_sub >= MIN_PATTERN

        evidence = []
        if count_sub >= MIN_PATTERN:
            evidence.append(f"{count_sub} sub-threshold transactions in {WINDOW_DAYS} days")
        if vol_spike > 2:
            evidence.append(f"Volume {vol_spike:.1f}x above client average")
        if below_by_pct > 0.05 and below_by_pct < 0.30:
            evidence.append(f"Amount is {below_by_pct*100:.1f}% below SAR 1M threshold")
        if total_sub > THRESHOLD_SAR * 2:
            evidence.append(f"Cumulative SAR {total_sub:,.0f} across {count_sub+1} transactions")

        explanation = (
            f"Structuring pattern detected: {count_sub} sub-threshold transfers from "
            f"the same counterparty totalling SAR {total_sub:,.0f} over {WINDOW_DAYS} days. "
            f"Current transaction of SAR {amount:,.0f} is "
            f"{below_by_pct*100:.1f}% below the SAR 1M reporting threshold. "
            f"Volume spike ratio: {vol_spike:.1f}x client average. "
            f"Recommended action: initiate EDD and file STR with SAFIU."
        ) if triggered else (
            f"No structuring pattern detected. Amount SAR {amount:,.0f}, "
            f"{count_sub} recent sub-threshold transactions."
        )

        return AgentFinding(
            agent_name=self.name,
            triggered=triggered,
            score=round(composite, 3),
            severity=AgentFinding(agent_name="", triggered=False, score=composite,
                                  severity="", pattern_type="", explanation="").risk_label
                    if False else ("critical" if composite >= 0.9 else
                                   "high" if composite >= 0.75 else
                                   "medium" if composite >= 0.45 else "low"),
            pattern_type="Structuring",
            explanation=explanation,
            shap_contributions=shap,
            recommended_action="Initiate EDD + File STR" if composite >= 0.75 else
                               "Flag for manual review" if triggered else "Clear",
            evidence=evidence,
        )

"""
Behavioral Anomaly Agent
Detects off-hours transactions, unusual volume spikes,
third-party payors, and other behavioral red flags.
Uses statistical deviation from client's own baseline.
"""
from agents.base_agent import BaseAgent, AgentFinding
from typing import Any
from datetime import time as dtime

BUSINESS_HOURS_START = dtime(8, 0)
BUSINESS_HOURS_END   = dtime(18, 0)
VOLUME_SPIKE_RATIO   = 3.0   # 3x above average = spike


class BehavioralAgent(BaseAgent):
    name = "BehavioralAgent"
    version = "1.0"

    def _analyze(self, context: dict[str, Any]) -> AgentFinding:
        txn           = context["transaction"]
        client        = context["client"]
        history       = context.get("client_history", [])

        amount        = txn["amount"]
        txn_datetime  = txn.get("datetime")
        txn_time      = txn_datetime.time() if txn_datetime else None
        third_party   = context.get("third_party_payor", False)
        client_avg    = context.get("client_avg_amount", amount)
        client_country= client.get("country", "")

        scores  = {}
        evidence= []

        # 1. Off-hours transaction
        scores["off_hours"] = 0.0
        if txn_time:
            is_off_hours = not (BUSINESS_HOURS_START <= txn_time <= BUSINESS_HOURS_END)
            if is_off_hours:
                scores["off_hours"] = 0.25
                evidence.append(f"Transaction initiated at {txn_time.strftime('%H:%M')} — outside business hours (08:00–18:00)")

        # 2. Unusual volume spike vs client baseline
        spike_ratio = amount / max(client_avg, 1)
        scores["volume_spike"] = min((spike_ratio - 1) / 10, 0.35) if spike_ratio > VOLUME_SPIKE_RATIO else 0.0
        if spike_ratio > VOLUME_SPIKE_RATIO:
            evidence.append(f"Volume {spike_ratio:.1f}x above client 6-month average (SAR {client_avg:,.0f})")

        # 3. Third-party payor (funds from someone other than named sender)
        scores["third_party_payor"] = 0.30 if third_party else 0.0
        if third_party:
            evidence.append("Payment instructed by a third party not named in the relationship")

        # 4. Frequency spike — sudden burst of transactions
        recent_count = len(history)
        expected_monthly = client.get("avg_monthly_txns", 5)
        freq_spike = recent_count / max(expected_monthly, 1)
        scores["frequency_spike"] = min((freq_spike - 1) / 5, 0.20) if freq_spike > 2.0 else 0.0
        if freq_spike > 2.0:
            evidence.append(f"Transaction frequency {freq_spike:.1f}x above client monthly average")

        # 5. New counterparty with large amount
        is_new_counterparty = client.get("total_txns", 0) < 2
        scores["new_counterparty"] = 0.15 if is_new_counterparty and amount > 500_000 else 0.0
        if scores["new_counterparty"]:
            evidence.append(f"Large SAR {amount:,.0f} transaction with a new / low-history counterparty")

        composite = min(sum(scores.values()), 1.0)
        triggered  = composite >= 0.25

        severity = ("critical" if composite >= 0.90 else
                    "high"     if composite >= 0.75 else
                    "medium"   if composite >= 0.45 else "low")

        explanation = (
            f"Behavioral anomaly detected (score {composite:.2f}): "
            + " | ".join(evidence)
        ) if triggered else (
            f"Behavior within normal parameters. Score {composite:.2f}."
        )

        return AgentFinding(
            agent_name=self.name,
            triggered=triggered,
            score=round(composite, 3),
            severity=severity,
            pattern_type="Off-Hours" if scores.get("off_hours", 0) > 0.20 else "Third-Party Payor" if third_party else "Behavioral Anomaly",
            explanation=explanation,
            shap_contributions={k: round(v, 3) for k, v in scores.items()},
            recommended_action=(
                "Flag for senior review + Request transaction justification" if triggered else "Clear"
            ),
            evidence=evidence,
        )

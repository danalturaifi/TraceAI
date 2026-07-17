"""
Layering & Circular Flow Detection Agent
Detects rapid fund turnaround and circular transaction patterns
that suggest funds are being layered to obscure their origin.
FATF Typology: Layering / Integration phase of money laundering
"""
from agents.base_agent import BaseAgent, AgentFinding
from typing import Any
from datetime import datetime, timedelta

RAPID_TURNAROUND_HOURS = 48
CIRCULAR_THRESHOLD     = 0.80   # outbound is 80%+ of a recent inbound


class LayeringAgent(BaseAgent):
    name = "LayeringAgent"
    version = "1.0"

    def _analyze(self, context: dict[str, Any]) -> AgentFinding:
        txn       = context["transaction"]
        history   = context.get("client_history", [])
        amount    = txn["amount"]
        txn_type  = txn.get("type", "")
        txn_time  = txn.get("datetime")

        evidence  = []
        scores    = {}

        # 1. Rapid fund turnaround — outbound shortly after large inbound
        rapid_turnaround_score = 0.0
        if txn_type == "Outbound Wire" and txn_time:
            recent_inbounds = [
                t for t in history
                if t.get("type") == "Inbound Wire"
                and t.get("datetime")
                and (txn_time - t["datetime"]).total_seconds() / 3600 <= RAPID_TURNAROUND_HOURS
            ]
            for inbound in recent_inbounds:
                ratio = amount / max(inbound["amount"], 1)
                if ratio >= CIRCULAR_THRESHOLD:
                    hours_gap = (txn_time - inbound["datetime"]).total_seconds() / 3600
                    rapid_turnaround_score = max(rapid_turnaround_score, ratio * 0.6)
                    evidence.append(
                        f"Outbound SAR {amount:,.0f} is {ratio*100:.0f}% of inbound "
                        f"SAR {inbound['amount']:,.0f} received {hours_gap:.1f}h ago"
                    )

        # 2. Multiple intermediary hops (inbound then immediately outbound pattern)
        hop_count = sum(
            1 for t in history
            if t.get("type") in ("Inbound Wire", "Outbound Wire")
            and txn_time
            and t.get("datetime")
            and abs((txn_time - t["datetime"]).total_seconds()) < 86400 * 7
        )
        hop_score = min(hop_count / 6, 1.0) * 0.25
        if hop_count >= 4:
            evidence.append(f"{hop_count} wire transfers in 7-day window — possible multi-hop layering")

        # 3. Same counterparty round-trip
        counterparty_id = txn.get("client_id")
        same_party_txns = [t for t in history if t.get("client_id") == counterparty_id]
        roundtrip_score = 0.0
        if len(same_party_txns) >= 2:
            roundtrip_score = 0.20
            evidence.append(
                f"Round-trip: {len(same_party_txns)} prior transactions with same counterparty"
            )

        # 4. No supporting commercial documentation
        has_invoice = context.get("has_commercial_invoice", False)
        invoice_score = 0.10 if not has_invoice and amount > 300_000 else 0.0
        if invoice_score:
            evidence.append("No commercial invoice submitted for large transfer")

        composite = min(
            rapid_turnaround_score + hop_score + roundtrip_score + invoice_score,
            1.0
        )

        shap = {
            "rapid_fund_turnaround":   round(rapid_turnaround_score, 3),
            "multi_hop_pattern":       round(hop_score, 3),
            "same_party_roundtrip":    round(roundtrip_score, 3),
            "missing_invoice":         round(invoice_score, 3),
        }

        triggered = composite >= 0.35

        severity = ("critical" if composite >= 0.9 else
                    "high"     if composite >= 0.75 else
                    "medium"   if composite >= 0.45 else "low")

        explanation = (
            f"Layering indicators detected (score {composite:.2f}): "
            + " | ".join(evidence)
        ) if triggered else (
            f"No layering pattern detected. Score {composite:.2f}."
        )

        return AgentFinding(
            agent_name=self.name,
            triggered=triggered,
            score=round(composite, 3),
            severity=severity,
            pattern_type="Layering",
            explanation=explanation,
            shap_contributions=shap,
            recommended_action=(
                "Block + Escalate to CCO + File STR" if composite >= 0.80 else
                "Flag for senior analyst review"     if triggered else
                "Clear"
            ),
            evidence=evidence,
        )

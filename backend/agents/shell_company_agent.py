"""
Shell Company & UBO Mismatch Detection Agent
Detects transactions involving shell entities, undisclosed UBOs,
or high-risk jurisdictions with no commercial justification.
FATF Typology: Corporate vehicles / beneficial ownership concealment
"""
from agents.base_agent import BaseAgent, AgentFinding
from typing import Any

# FATF high-risk / non-cooperative jurisdictions (subset)
HIGH_RISK_JURISDICTIONS = {
    "VG", "KY", "BM", "BS", "PA", "LR", "MM", "KP", "IR",
    "SY", "YE", "SS", "AF", "HT", "LA", "PK",
}

# Jurisdictions requiring enhanced scrutiny
ENHANCED_SCRUTINY = {
    "SD", "LB", "IQ", "LY", "SO", "ML", "CF", "CD",
}

SHELL_INDICATORS = [
    "no_commercial_history",
    "ubo_undisclosed",
    "kyc_failed",
    "registered_agent_only",
    "nominee_directors",
]


class ShellCompanyAgent(BaseAgent):
    name = "ShellCompanyAgent"
    version = "1.2"

    def _analyze(self, context: dict[str, Any]) -> AgentFinding:
        txn    = context["transaction"]
        client = context["client"]

        country        = client.get("country", "")
        is_shell       = client.get("is_shell", False)
        kyc_status     = client.get("kyc_status", "verified")
        ubo_name       = client.get("ubo_name")
        entity_type    = client.get("entity_type", "Corporate")
        amount         = txn["amount"]
        has_invoice    = context.get("has_commercial_invoice", False)
        total_txns     = client.get("total_txns", 0)

        # Feature scores
        score_jurisdiction = (
            0.50 if country in HIGH_RISK_JURISDICTIONS else
            0.25 if country in ENHANCED_SCRUTINY else 0.0
        )
        score_kyc          = 0.30 if kyc_status == "failed" else 0.15 if kyc_status == "pending" else 0.0
        score_shell        = 0.40 if is_shell else 0.0
        score_ubo          = 0.20 if not ubo_name else 0.0
        score_no_history   = 0.15 if total_txns < 3 else 0.0
        score_no_invoice   = 0.10 if not has_invoice and amount > 500_000 else 0.0

        composite = min(
            score_jurisdiction + score_kyc + score_shell +
            score_ubo + score_no_history + score_no_invoice,
            1.0
        )

        shap = {
            "high_risk_jurisdiction": round(score_jurisdiction, 3),
            "kyc_failure":            round(score_kyc, 3),
            "shell_entity_flag":      round(score_shell, 3),
            "ubo_not_disclosed":      round(score_ubo, 3),
            "no_transaction_history": round(score_no_history, 3),
            "no_commercial_invoice":  round(score_no_invoice, 3),
        }

        triggered = composite >= 0.35

        evidence = []
        if country in HIGH_RISK_JURISDICTIONS:
            evidence.append(f"Jurisdiction {country} is FATF high-risk / non-cooperative")
        if country in ENHANCED_SCRUTINY:
            evidence.append(f"Jurisdiction {country} requires enhanced scrutiny")
        if is_shell:
            evidence.append("Client entity classified as shell company")
        if kyc_status in ("failed", "pending"):
            evidence.append(f"KYC status: {kyc_status}")
        if not ubo_name:
            evidence.append("Ultimate Beneficial Owner not disclosed")
        if total_txns < 3:
            evidence.append(f"Only {total_txns} transactions on record — no commercial history")
        if not has_invoice and amount > 500_000:
            evidence.append(f"No commercial invoice for SAR {amount:,.0f} transfer")

        severity = ("critical" if composite >= 0.9 else
                    "high"     if composite >= 0.75 else
                    "medium"   if composite >= 0.45 else "low")

        explanation = (
            f"Shell company / UBO concealment indicators: score {composite:.2f}. "
            + " | ".join(evidence) + ". "
            f"Top risk driver: {'FATF high-risk jurisdiction ' + country if country in HIGH_RISK_JURISDICTIONS else 'shell entity classification'}."
        ) if triggered else (
            f"No shell company indicators. Jurisdiction {country}, KYC {kyc_status}."
        )

        return AgentFinding(
            agent_name=self.name,
            triggered=triggered,
            score=round(composite, 3),
            severity=severity,
            pattern_type="Shell Company" if is_shell else "UBO Mismatch",
            explanation=explanation,
            shap_contributions=shap,
            recommended_action=(
                "Block transaction + File STR immediately" if composite >= 0.80 else
                "Initiate EDD + Request UBO documentation" if triggered else
                "Clear"
            ),
            evidence=evidence,
        )

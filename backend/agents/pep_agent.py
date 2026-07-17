"""
PEP Linkage & Sanctions Screening Agent
Screens counterparties against PEP lists and sanctions watchlists.
In production: integrate with Refinitiv World-Check, Dow Jones Risk,
or SAMA's national watchlist via API. Here we simulate the logic.
SAMA AML Regulation Article 18: Enhanced Due Diligence for PEPs
"""
from agents.base_agent import BaseAgent, AgentFinding
from typing import Any

# Simulated PEP / sanctions indicators (in production: external API call)
PEP_JURISDICTIONS = {"SD", "SY", "KP", "IR", "MM", "YE", "LY", "SS"}

class PEPAgent(BaseAgent):
    name = "PEPAgent"
    version = "1.1"

    def _analyze(self, context: dict[str, Any]) -> AgentFinding:
        client  = context["client"]
        txn     = context["transaction"]

        is_pep       = client.get("is_pep", False)
        country      = client.get("country", "")
        kyc_status   = client.get("kyc_status", "verified")
        amount       = txn["amount"]
        is_inbound   = txn.get("type", "") == "Inbound Wire"

        scores = {}
        evidence = []

        # Direct PEP flag
        scores["direct_pep_flag"] = 0.60 if is_pep else 0.0
        if is_pep:
            evidence.append("Client is flagged as Politically Exposed Person (PEP)")

        # PEP-risk jurisdiction
        scores["pep_jurisdiction"] = 0.35 if country in PEP_JURISDICTIONS else 0.0
        if country in PEP_JURISDICTIONS:
            evidence.append(f"Counterparty country {country} has elevated PEP risk")

        # Large inbound from PEP-linked party raises ML risk significantly
        scores["large_pep_inbound"] = 0.20 if is_inbound and amount > 1_000_000 else 0.0
        if is_inbound and amount > 1_000_000 and (is_pep or country in PEP_JURISDICTIONS):
            evidence.append(f"Large inbound SAR {amount:,.0f} from PEP-linked jurisdiction")

        # KYC issues compound PEP risk
        scores["kyc_gap_with_pep"] = (
            0.20 if (is_pep or country in PEP_JURISDICTIONS) and kyc_status in ("failed", "pending") else 0.0
        )
        if scores["kyc_gap_with_pep"]:
            evidence.append(f"KYC {kyc_status} — cannot verify relationship for PEP-linked entity")

        composite = min(sum(scores.values()), 1.0)
        triggered  = composite >= 0.30

        severity = ("critical" if composite >= 0.90 else
                    "high"     if composite >= 0.75 else
                    "medium"   if composite >= 0.45 else "low")

        explanation = (
            f"PEP / sanctions concern detected (score {composite:.2f}). "
            + " | ".join(evidence) + ". "
            "SAMA AML Regulations require mandatory EDD for all PEP-linked transactions."
        ) if triggered else (
            f"No PEP linkage detected. Jurisdiction {country}, PEP flag: {is_pep}."
        )

        return AgentFinding(
            agent_name=self.name,
            triggered=triggered,
            score=round(composite, 3),
            severity=severity,
            pattern_type="PEP Linkage",
            explanation=explanation,
            shap_contributions={k: round(v, 3) for k, v in scores.items()},
            recommended_action=(
                "Mandatory EDD + CCO approval required before processing" if is_pep else
                "Enhanced scrutiny + document source of funds"            if triggered else
                "Clear"
            ),
            evidence=evidence,
        )

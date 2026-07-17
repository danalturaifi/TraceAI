# %% [markdown]
# # TraceAI — AI Agent Analysis Notebook
# Run this in Jupyter / Anaconda to test agents on hypothetical transaction data.
# All data below is fictional — AlNakheel Trading Co.

# %%
import sys, json
sys.path.insert(0, "..")   # add backend/ to path

from agents.orchestrator import analyze_transaction
from datetime import datetime

# %% [markdown]
# ## Test Case 1: Structuring Pattern (Gulf Commodities LLC)

# %%
ctx_structuring = {
    "transaction": {
        "id": "TXN-2026-00891",
        "amount": 4_850_000,
        "currency": "SAR",
        "type": "Inbound Wire",
        "channel": "SWIFT",
        "client_id": "C001",
        "datetime": datetime(2026, 6, 30, 10, 22),
    },
    "client": {
        "id": "C001",
        "name": "Gulf Commodities LLC",
        "country": "AE",
        "kyc_status": "expired",
        "is_pep": False,
        "is_shell": False,
        "ubo_name": "Khalid Al-Farsi",
        "entity_type": "Corporate",
        "total_txns": 47,
    },
    "client_history": [
        {"id": f"TXN-HIST-{i}", "amount": 900_000 + i*10_000, "type": "Inbound Wire",
         "client_id": "C001", "datetime": datetime(2026, 6, 30-i, 10, 0)}
        for i in range(1, 6)
    ],
    "client_avg_amount": 800_000,
    "has_commercial_invoice": False,
    "third_party_payor": False,
}

result = analyze_transaction(ctx_structuring)

print(f"=== Composite Score: {result.composite_score:.3f} ({result.severity.upper()}) ===")
print(f"Top Pattern      : {result.top_pattern}")
print(f"Recommended      : {result.recommended_action}")
print(f"Should Block     : {result.should_block}")
print(f"Should File STR  : {result.should_file_str}")
print(f"\nExplanation:\n{result.unified_explanation}")
print(f"\nSHAP Contributions:\n{json.dumps(result.shap_summary, indent=2)}")

# %% [markdown]
# ## Test Case 2: Shell Company — Pinnacle Holdings BVI

# %%
ctx_shell = {
    "transaction": {
        "id": "TXN-2026-00890",
        "amount": 2_100_000,
        "currency": "SAR",
        "type": "Outbound Wire",
        "channel": "SWIFT",
        "client_id": "C009",
        "datetime": datetime(2026, 6, 30, 9, 47),
    },
    "client": {
        "id": "C009",
        "name": "Pinnacle Holdings BVI",
        "country": "VG",   # British Virgin Islands — FATF high-risk
        "kyc_status": "failed",
        "is_pep": False,
        "is_shell": True,
        "ubo_name": None,
        "entity_type": "Shell",
        "total_txns": 6,
    },
    "client_history": [],
    "client_avg_amount": 500_000,
    "has_commercial_invoice": False,
    "third_party_payor": False,
}

result2 = analyze_transaction(ctx_shell)

print(f"=== Score: {result2.composite_score:.3f} ({result2.severity.upper()}) ===")
print(f"Recommended: {result2.recommended_action}")
print(f"Block: {result2.should_block} | STR: {result2.should_file_str}")
for f in result2.triggered_agents:
    print(f"\n[{f.agent_name}] Score: {f.score:.3f}")
    print(f"  {f.explanation[:200]}")

# %% [markdown]
# ## Visualize SHAP contributions

# %%
import matplotlib.pyplot as plt
import numpy as np

def plot_shap(result, title="SHAP Feature Contributions"):
    shap = result.shap_summary
    features = list(shap.keys())
    values   = list(shap.values())

    colors = ["#ef4444" if v > 0.15 else "#f59e0b" if v > 0.05 else "#06b6d4"
              for v in values]

    fig, ax = plt.subplots(figsize=(10, max(4, len(features) * 0.5)))
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0a0f1e")

    bars = ax.barh(features, values, color=colors, height=0.6)
    ax.set_xlabel("Contribution to Risk Score", color="#94a3b8")
    ax.set_title(title, color="#f8fafc", fontsize=13, fontweight="bold")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_edgecolor("#1e293b")

    for bar, val in zip(bars, values):
        ax.text(val + 0.005, bar.get_y() + bar.get_height()/2,
                f"{val:.3f}", va="center", color="#f8fafc", fontsize=9)

    plt.tight_layout()
    plt.savefig(f"shap_{title[:20].replace(' ','_')}.png", dpi=150,
                facecolor=fig.get_facecolor())
    plt.show()

plot_shap(result,  "Structuring — Gulf Commodities")
plot_shap(result2, "Shell Company — Pinnacle BVI")

# %% [markdown]
# ## Batch analysis — run all 15 hypothetical transactions

# %%
HYPOTHETICAL_TXNS = [
    {"id": "TXN-2026-00891", "amount": 4_850_000, "type": "Inbound Wire",  "country": "AE", "kyc": "expired",  "shell": False, "pep": False, "avg": 800_000,  "history_count": 5, "off_hours": False, "third_party": False},
    {"id": "TXN-2026-00890", "amount": 2_100_000, "type": "Outbound Wire", "country": "VG", "kyc": "failed",   "shell": True,  "pep": False, "avg": 500_000,  "history_count": 1, "off_hours": False, "third_party": False},
    {"id": "TXN-2026-00889", "amount":   980_000, "type": "Inbound Wire",  "country": "AE", "kyc": "failed",   "shell": False, "pep": False, "avg": 400_000,  "history_count": 3, "off_hours": False, "third_party": False},
    {"id": "TXN-2026-00888", "amount": 3_300_000, "type": "Inbound Wire",  "country": "SD", "kyc": "pending",  "shell": False, "pep": True,  "avg": 900_000,  "history_count": 2, "off_hours": False, "third_party": False},
    {"id": "TXN-2026-00887", "amount":   540_000, "type": "Outbound Wire", "country": "SA", "kyc": "verified", "shell": False, "pep": False, "avg": 600_000,  "history_count": 10,"off_hours": False, "third_party": False},
    {"id": "TXN-2026-00886", "amount": 1_750_000, "type": "Inbound Wire",  "country": "EG", "kyc": "pending",  "shell": False, "pep": False, "avg": 700_000,  "history_count": 2, "off_hours": False, "third_party": False},
    {"id": "TXN-2026-00885", "amount":   870_000, "type": "Inbound Wire",  "country": "AE", "kyc": "failed",   "shell": False, "pep": False, "avg": 400_000,  "history_count": 3, "off_hours": True,  "third_party": False},
    {"id": "TXN-2026-00884", "amount":   660_000, "type": "Outbound Wire", "country": "LB", "kyc": "verified", "shell": False, "pep": False, "avg": 550_000,  "history_count": 8, "off_hours": False, "third_party": False},
    {"id": "TXN-2026-00883", "amount": 2_200_000, "type": "Inbound Wire",  "country": "SA", "kyc": "verified", "shell": False, "pep": False, "avg": 2_000_000,"history_count": 20,"off_hours": False, "third_party": False},
    {"id": "TXN-2026-00882", "amount": 1_200_000, "type": "Outbound Wire", "country": "AE", "kyc": "expired",  "shell": False, "pep": False, "avg": 800_000,  "history_count": 5, "off_hours": False, "third_party": False},
    {"id": "TXN-2026-00881", "amount":   450_000, "type": "Inbound Wire",  "country": "KW", "kyc": "verified", "shell": False, "pep": False, "avg": 400_000,  "history_count": 15,"off_hours": False, "third_party": False},
    {"id": "TXN-2026-00880", "amount":   980_000, "type": "Inbound Wire",  "country": "SD", "kyc": "pending",  "shell": False, "pep": False, "avg": 500_000,  "history_count": 2, "off_hours": False, "third_party": True},
    {"id": "TXN-2026-00879", "amount": 1_600_000, "type": "Inbound Wire",  "country": "VG", "kyc": "failed",   "shell": True,  "pep": False, "avg": 200_000,  "history_count": 1, "off_hours": False, "third_party": False},
    {"id": "TXN-2026-00878", "amount":   310_000, "type": "Outbound Wire", "country": "SA", "kyc": "verified", "shell": False, "pep": False, "avg": 350_000,  "history_count": 30,"off_hours": False, "third_party": False},
    {"id": "TXN-2026-00877", "amount":   990_000, "type": "Inbound Wire",  "country": "AE", "kyc": "expired",  "shell": False, "pep": False, "avg": 600_000,  "history_count": 5, "off_hours": False, "third_party": False},
]

results = []
for t in HYPOTHETICAL_TXNS:
    ctx = {
        "transaction": {"id": t["id"], "amount": t["amount"], "type": t["type"],
                        "client_id": "C_DEMO", "datetime": datetime(2026, 6, 30, 10, 0)},
        "client": {"id": "C_DEMO", "country": t["country"], "kyc_status": t["kyc"],
                   "is_shell": t["shell"], "is_pep": t["pep"], "ubo_name": "Test",
                   "entity_type": "Shell" if t["shell"] else "Corporate", "total_txns": t["history_count"]},
        "client_history": [
            {"id": f"H{i}", "amount": t["avg"] * 0.9, "type": "Inbound Wire",
             "client_id": "C_DEMO", "datetime": datetime(2026, 6, 30-i, 10, 0)}
            for i in range(1, t["history_count"] + 1)
        ],
        "client_avg_amount": t["avg"],
        "has_commercial_invoice": t["kyc"] == "verified",
        "third_party_payor": t["third_party"],
    }
    r = analyze_transaction(ctx)
    results.append({"id": t["id"], "score": r.composite_score, "severity": r.severity,
                    "pattern": r.top_pattern, "block": r.should_block, "str": r.should_file_str})

import pandas as pd
df = pd.DataFrame(results)
print(df.to_string(index=False))
print(f"\nTriggered blocks: {df['block'].sum()} / {len(df)}")
print(f"STR recommended:  {df['str'].sum()} / {len(df)}")
print(f"Avg risk score:   {df['score'].mean():.3f}")

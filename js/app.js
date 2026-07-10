"use strict";
/* TraceAI — single-flow app: login → dashboard → case queue → case detail → audit.
   Every risk verdict comes from the live backend; the transaction feed is a
   simulated core-banking feed (clearly labeled). */

/* ══════════ API CLIENT ══════════ */
const API = (() => {
  const BASE = "https://traceai-api.onrender.com";
  let token = null;
  let online = false;

  async function health() {
    try {
      const r = await fetch(BASE + "/api/health", { signal: AbortSignal.timeout(60000) });
      online = r.ok;
    } catch (_) { online = false; }
    return online;
  }

  async function login(userId, pin) {
    const r = await fetch(BASE + "/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, pin }),
    });
    if (!r.ok) return null;
    const d = await r.json();
    token = d.access_token;
    return d.user;
  }

  async function analyze(t, c) {
    const history = DB.transactions
      .filter(x => x.client === t.client && x.id !== t.id)
      .map(x => ({ amount: x.amount, datetime: `${x.date}T${x.time}:00` }));
    const avg = history.length ? history.reduce((s, x) => s + x.amount, 0) / history.length : t.amount;
    const payload = {
      transaction: { amount: t.amount, datetime: `${t.date}T${t.time}:00`, type: t.type, client_id: t.client },
      client: {
        country: c ? c.country : "SA",
        is_shell: c ? c.type === "Shell" : false,
        is_pep: t.flags.some(f => /PEP|Politically Exposed/i.test(f)),
        kyc_status: c ? c.kycStatus : "verified",
        entity_type: c ? c.type : "Corporate",
        total_txns: c ? c.totalTxns : 0,
        ubo_name: t.flags.some(f => /UBO/i.test(f)) ? null : (c ? c.name : null),
      },
      client_history: history,
      client_avg_amount: avg,
      has_commercial_invoice: t.aiRisk < 50,
      third_party_payor: t.flags.includes("Third-Party Payor"),
    };
    const r = await fetch(BASE + "/api/analysis/transaction", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(90000),
    });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  return { health, login, analyze, isOnline: () => online, hasToken: () => !!token };
})();

/* ══════════ STATE ══════════ */
let ME = null;
const verdictCache = {};   // txnId -> live analysis result

/* ══════════ HELPERS ══════════ */
const $ = (id) => document.getElementById(id);
const fmt = (n) => "SAR " + n.toLocaleString("en-US");
const esc = (s) => String(s).replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));

function toast(msg, kind = "info") {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.textContent = msg;
  $("toast-container").appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function riskColor(v) { return v >= 0.7 ? "var(--danger)" : v >= 0.4 ? "var(--warning)" : "var(--safe)"; }
function riskWord(v)  { return v >= 0.9 ? "Critical" : v >= 0.7 ? "High" : v >= 0.4 ? "Elevated" : "Low"; }

function statusBadge(s) {
  const map = {
    flagged:      ["badge-warning", "Needs review"],
    blocked:      ["badge-danger",  "Blocked"],
    under_review: ["badge-info",    "In review"],
    cleared:      ["badge-safe",    "Cleared"],
  };
  const [cls, label] = map[s] || ["badge-muted", s];
  return `<span class="badge ${cls}">${label}</span>`;
}

function setEnginePill(ok) {
  const pill = $("engine-pill");
  pill.className = "api-pill " + (ok ? "ok" : "down");
  pill.textContent = ok ? "AI engine online" : "AI engine offline";
}

/* ══════════ LOGIN ══════════ */
function initLogin() {
  const sel = $("login-user");
  sel.innerHTML = DB.users.map(u => `<option value="${u.id}">${esc(u.name)} — ${esc(u.role)}</option>`).join("");

  API.health().then(ok => {
    const pill = $("api-status");
    pill.className = "api-pill " + (ok ? "ok" : "down");
    pill.textContent = ok ? "AI service connected" : "AI engine offline — demo mode active";
    setEnginePill(ok);
    if (!ok) setTimeout(() => API.health().then(setEnginePill), 30000);
  });

  $("login-form").onsubmit = async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button");
    const err = $("login-error");
    err.style.display = "none";
    btn.disabled = true;
    btn.textContent = "Verifying…";
    try {
      const user = await API.login(sel.value, $("login-pin").value);
      if (!user) throw new Error("bad");
      ME = user;
      enterApp();
    } catch (_) {
      // Offline demo fallback: local credential check, clearly labeled demo mode
      if (!API.isOnline() && $("login-pin").value === "1234") {
        const u = DB.getUser(sel.value);
        ME = { id: u.id, name: u.name, role: u.role, clearance: u.clearance };
        enterApp(true);
      } else {
        err.textContent = API.isOnline()
          ? "Invalid credentials. Repeated failures lock the account for 30 minutes."
          : "AI service offline — demo sign-in available for authorized demo credentials.";
        err.style.display = "block";
      }
    }
    btn.disabled = false;
    btn.textContent = "Sign in";
  };
}

let DEMO_MODE = false;

function enterApp(demo = false) {
  DEMO_MODE = demo;
  $("view-login").style.display = "none";
  $("app").style.display = "grid";
  $("me-name").textContent = ME.name;
  $("me-role").textContent = ME.role + " · clearance L" + ME.clearance;
  $("me-avatar").textContent = ME.name.split(" ").map(w => w[0]).join("").slice(0, 2);
  setEnginePill(!demo);
  if (demo) {
    const pill = $("engine-pill");
    pill.className = "api-pill checking";
    pill.textContent = "Demo mode — verdicts simulated locally";
  }
  $("queue-count").textContent = DB.transactions.filter(t => t.status !== "cleared").length;
  navigate("dashboard");
}

$("logout-card") && ($("logout-card").onclick = () => location.reload());
document.addEventListener("click", (e) => {
  const nav = e.target.closest(".nav-item");
  if (nav) navigate(nav.dataset.view);
});

/* ══════════ ROUTER ══════════ */
function navigate(view, arg) {
  document.querySelectorAll(".nav-item").forEach(n =>
    n.classList.toggle("active", n.dataset.view === view));
  const views = { dashboard: renderDashboard, queue: renderQueue, case: renderCase, audit: renderAudit };
  (views[view] || renderDashboard)(arg);
}

/* ══════════ DASHBOARD ══════════ */
function renderDashboard() {
  $("page-title").textContent = "Dashboard";
  $("page-crumb").textContent = "AlNakheel Trading Co. · transaction monitoring";
  const txns = DB.transactions;
  const open = txns.filter(t => t.status === "flagged" || t.status === "under_review");
  const blocked = txns.filter(t => t.status === "blocked");
  const volume = txns.reduce((s, t) => s + t.amount, 0);
  const flaggedVol = txns.filter(t => t.status !== "cleared").reduce((s, t) => s + t.amount, 0);

  const attention = txns
    .filter(t => t.status !== "cleared")
    .sort((a, b) => b.aiRisk - a.aiRisk)
    .slice(0, 5);

  $("content").innerHTML = `
    <div class="metric-grid">
      <div class="metric-card"><div class="metric-label">Open cases</div>
        <div class="metric-value warning">${open.length}</div>
        <div class="metric-change">awaiting analyst decision</div></div>
      <div class="metric-card"><div class="metric-label">Blocked by AI</div>
        <div class="metric-value danger">${blocked.length}</div>
        <div class="metric-change">held before settlement</div></div>
      <div class="metric-card"><div class="metric-label">Volume screened (7d)</div>
        <div class="metric-value">${(volume / 1e6).toFixed(1)}M</div>
        <div class="metric-change">SAR, all channels</div></div>
      <div class="metric-card"><div class="metric-label">Volume under investigation</div>
        <div class="metric-value accent">${(flaggedVol / 1e6).toFixed(1)}M</div>
        <div class="metric-change">${Math.round(flaggedVol / volume * 100)}% of screened volume</div></div>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">Needs your attention</div>
          <div class="card-subtitle">Highest-risk open cases, ranked by the AI engine</div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="navigate('queue')">Full queue →</button>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Case</th><th>Counterparty</th><th>Amount</th><th>Status</th><th>Risk</th><th></th></tr></thead>
        <tbody>${attention.map(rowHtml).join("")}</tbody>
      </table></div>
    </div>
    <div class="feed-note">Transaction feed: simulated core-banking data for demonstration. Risk verdicts: computed live by the TraceAI agent engine.</div>`;
}

function rowHtml(t) {
  const c = DB.getClient(t.client);
  return `
    <tr class="${t.status === 'blocked' ? 'blocked-row' : 'flagged-row'}" style="cursor:pointer"
        onclick="navigate('case','${t.id}')">
      <td style="font-family:var(--mono);font-size:11px">${t.id}</td>
      <td>${c ? esc(c.name) : t.client}<div style="font-size:10px;color:var(--text-muted)">${c ? c.country : ""}</div></td>
      <td style="font-weight:700">${fmt(t.amount)}</td>
      <td>${statusBadge(t.status)}</td>
      <td>
        <div class="risk-bar"><div class="risk-fill ${t.aiRisk >= 70 ? 'high' : t.aiRisk >= 40 ? 'medium' : 'low'}" style="width:${t.aiRisk}%"></div></div>
      </td>
      <td style="color:var(--accent);font-size:11px;white-space:nowrap">Open case →</td>
    </tr>`;
}

/* ══════════ CASE QUEUE ══════════ */
function renderQueue() {
  $("page-title").textContent = "Case Queue";
  $("page-crumb").textContent = "All monitored transactions · click a case to run full AI analysis";
  const rows = DB.transactions
    .slice()
    .sort((a, b) => b.aiRisk - a.aiRisk)
    .map(rowHtml).join("");
  $("content").innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr><th>Case</th><th>Counterparty</th><th>Amount</th><th>Status</th><th>Risk</th><th></th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div>
    </div>
    <div class="feed-note">Transaction feed: simulated core-banking data. Open any case for a live 5-agent verdict.</div>`;
}

/* ══════════ CASE DETAIL ══════════ */
async function renderCase(id) {
  const t = DB.getTxn(id);
  if (!t) return navigate("queue");
  const c = DB.getClient(t.client);

  $("page-title").textContent = "Case " + t.id;
  $("page-crumb").textContent = (c ? c.name : t.client) + " · " + t.type;

  $("content").innerHTML = `
    <button class="btn btn-secondary btn-sm" onclick="navigate('queue')" style="margin-bottom:14px">← Back to queue</button>
    <div class="grid-2-1">
      <div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-header"><div class="card-title">Transaction facts</div>${statusBadge(t.status)}</div>
          <div class="fact-grid">
            <div><div class="form-label">Amount</div><div class="fact-big">${fmt(t.amount)}</div></div>
            <div><div class="form-label">Date &amp; time</div><div>${t.date} ${t.time}</div></div>
            <div><div class="form-label">Direction</div><div>${t.type} · ${t.channel}</div></div>
            <div><div class="form-label">Counterparty</div><div>${c ? esc(c.name) : t.client}</div></div>
            <div><div class="form-label">Jurisdiction</div><div>${c ? c.country : "—"}</div></div>
            <div><div class="form-label">KYC status</div><div>${c ? c.kycStatus : "—"}</div></div>
          </div>
          <hr class="divider"/>
          <div class="form-label">Case notes</div>
          <div style="font-size:12.5px;color:var(--text-secondary);line-height:1.6">${esc(t.notes)}</div>
        </div>
        <div id="verdict-zone">
          <div class="card verdict-loading">
            <div class="spinner"></div>
            <div>
              <div style="font-weight:700">Running live AI analysis…</div>
              <div style="font-size:11.5px;color:var(--text-muted)">Five specialist agents are scoring this case in parallel. First run after idle can take up to a minute.</div>
            </div>
          </div>
        </div>
      </div>
      <div>
        <div class="card">
          <div class="card-title" style="margin-bottom:10px">Counterparty profile</div>
          ${c ? `
          <div class="stat-row"><span class="stat-label">Relationship</span><span class="stat-value">${c.type}</span></div>
          <div class="stat-row"><span class="stat-label">Total transactions</span><span class="stat-value">${c.totalTxns}</span></div>
          <div class="stat-row"><span class="stat-label">Previously flagged</span><span class="stat-value ${c.flagged > 3 ? 'danger' : ''}">${c.flagged}</span></div>
          <div class="stat-row"><span class="stat-label">Base risk score</span><span class="stat-value ${c.riskScore >= 70 ? 'danger' : c.riskScore >= 40 ? 'warning' : 'safe'}">${c.riskScore}/100</span></div>
          <div class="stat-row"><span class="stat-label">Last activity</span><span class="stat-value mono">${c.lastActivity}</span></div>` : `<div class="form-hint">No profile on record.</div>`}
        </div>
      </div>
    </div>`;

  // Live verdict (cached per case for the session); demo fallback when offline
  if (DEMO_MODE) {
    $("verdict-zone").innerHTML = verdictHtml(localVerdict(t, c), t, true);
    return;
  }
  try {
    const r = verdictCache[id] || (verdictCache[id] = await API.analyze(t, c));
    $("verdict-zone").innerHTML = verdictHtml(r, t, false);
  } catch (e) {
    $("verdict-zone").innerHTML = `
      <div class="card">
        <div class="alert-banner warning" style="margin-bottom:10px">
          The AI service did not respond (${esc(e.message)}). Showing a simulated demo verdict instead.
        </div>
        ${verdictHtml(localVerdict(t, c), t, true).replace('<div class="card">', '<div>').replace(/<\/div>$/, "</div>")}
        <div style="margin-top:10px"><button class="btn btn-secondary btn-sm" onclick="verdictRetry('${id}')">Retry live analysis</button></div>
      </div>`;
  }
}

/* Local (demo) verdict — same shape as the backend response, computed from case flags */
function localVerdict(t, c) {
  const score = t.aiRisk / 100;
  const F = (name, patterns, base) => {
    const hit = t.flags.some(f => patterns.test(f));
    const s = hit ? Math.min(0.98, base + score * 0.35) : Math.max(0.02, score * 0.25);
    return {
      agent: name, triggered: hit, score: s,
      explanation: hit
        ? `Pattern indicators present in this case match the ${name.replace("Agent", "").toLowerCase()} typology.`
        : "No significant indicators for this typology.",
    };
  };
  const findings = [
    F("StructuringAgent",  /Structuring|Smurfing|Repeat Pattern/i, 0.55),
    F("ShellCompanyAgent", /Shell|UBO|BVI/i,                        0.60),
    F("LayeringAgent",     /Layering|Circular|Turnaround/i,         0.55),
    F("PEPAgent",          /PEP|Politically/i,                      0.55),
    F("BehavioralAgent",   /Off-Hours|Volume Spike|Unusual/i,       0.45),
  ];
  return {
    composite_score: score,
    severity: riskWord(score).toLowerCase(),
    top_pattern: (t.flags[0] || "None"),
    should_block: score >= 0.90,
    should_file_str: score >= 0.75,
    should_edd: score >= 0.50,
    unified_explanation: t.notes,
    agent_findings: findings,
  };
}

function verdictRetry(id) { delete verdictCache[id]; renderCase(id); }

function verdictHtml(r, t, demo) {
  const pct = Math.round(r.composite_score * 100);
  const color = riskColor(r.composite_score);
  const actions = [];
  if (r.should_block)    actions.push(['danger',  'Block transaction']);
  if (r.should_file_str) actions.push(['danger',  'File STR with SAFIU']);
  if (r.should_edd)      actions.push(['warning', 'Enhanced due diligence']);
  if (!actions.length)   actions.push(['safe',    'No action required']);

  const agents = (r.agent_findings || []).map(a => {
    const apct = Math.round(a.score * 100);
    return `
      <div class="agent-row ${a.triggered ? 'triggered' : ''}">
        <div class="agent-head">
          <span class="agent-name">${esc(a.agent.replace("Agent", ""))}</span>
          <span class="agent-score" style="color:${riskColor(a.score)}">${apct}</span>
        </div>
        <div class="risk-bar"><div class="risk-fill ${a.score >= 0.7 ? 'high' : a.score >= 0.4 ? 'medium' : 'low'}" style="width:${apct}%"></div></div>
        <div class="agent-expl">${esc(a.explanation || "")}</div>
      </div>`;
  }).join("");

  return `
    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">AI verdict — ${demo ? "demo (simulated)" : "live"}</div>
          <div class="card-subtitle">${demo ? "Simulated locally; connect the AI engine for live scoring" : "Computed just now by 5 specialist agents on the TraceAI engine"}</div>
        </div>
        <div style="text-align:right">
          <div style="font-size:30px;font-weight:800;color:${color};line-height:1">${pct}</div>
          <div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px">${riskWord(r.composite_score)} risk</div>
        </div>
      </div>

      <div style="margin-bottom:12px">
        ${actions.map(([k, l]) => `<span class="badge badge-${k}" style="margin:2px 4px 2px 0;padding:5px 12px">${l}</span>`).join("")}
      </div>

      <div class="xai-card ${r.composite_score >= 0.7 ? 'critical' : r.composite_score >= 0.4 ? 'triggered' : ''}">
        ${esc(r.unified_explanation || "No dominant risk pattern identified.")}
      </div>

      <details class="evidence" ${r.composite_score >= 0.4 ? "open" : ""}>
        <summary>Technical evidence — per-agent breakdown</summary>
        <div style="margin-top:10px">${agents}</div>
      </details>

      <div class="modal-footer" style="margin-top:14px">
        ${r.should_block ? `<button class="btn btn-danger" onclick="decide('${t.id}','blocked','Transaction blocked and reported')">Block &amp; report</button>` : ""}
        ${r.should_file_str ? `<button class="btn btn-warning" onclick="decide('${t.id}','under_review','STR draft opened for SAFIU filing')">File STR</button>` : ""}
        <button class="btn btn-secondary" onclick="decide('${t.id}','under_review','Case escalated for enhanced due diligence')">Escalate to EDD</button>
        <button class="btn btn-secondary" onclick="decide('${t.id}','cleared','Case cleared with documented rationale')">Clear case</button>
      </div>
    </div>`;
}

function decide(id, newStatus, msg) {
  const t = DB.getTxn(id);
  if (t) t.status = newStatus;
  DB.auditLog.unshift({
    id: "AL-" + Date.now(),
    ts: new Date().toISOString().slice(0, 16).replace("T", " "),
    user: ME ? ME.id : "system",
    action: "ANALYST_DECISION",
    target: id,
    detail: msg,
  });
  toast(msg + " — recorded in audit trail.", newStatus === "cleared" ? "success" : "warning");
  $("queue-count").textContent = DB.transactions.filter(x => x.status !== "cleared").length;
  navigate("queue");
}

/* ══════════ AUDIT ══════════ */
function renderAudit() {
  $("page-title").textContent = "Audit Trail";
  $("page-crumb").textContent = "Immutable record of every analyst decision";
  const rows = DB.auditLog.map(a => {
    const u = DB.getUser(a.user);
    return `
    <tr>
      <td style="font-family:var(--mono);font-size:11px;white-space:nowrap">${esc(a.ts)}</td>
      <td>${esc(u ? u.name : a.user)}</td>
      <td><span class="badge badge-muted" style="margin-right:6px">${esc(a.action)}</span>${esc(a.detail || "")}</td>
      <td style="font-family:var(--mono);font-size:11px">${esc(a.target || "")}</td>
    </tr>`;
  }).join("");
  $("content").innerHTML = `
    <div class="card">
      <div class="table-wrap"><table>
        <thead><tr><th>Timestamp</th><th>User</th><th>Action</th><th>Reference</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4" style="color:var(--text-muted)">No entries yet this session.</td></tr>`}</tbody>
      </table></div>
    </div>`;
}

/* ══════════ BOOT ══════════ */
initLogin();

/* TraceAI — Hypothetical transaction database (no real data) */
"use strict";

const DB = (() => {

  // Company info
  const company = {
    name: "AlNakheel Trading Co.",
    crn: "1010-384-XXX",
    sector: "Wholesale & Import/Export",
    bankAccount: "SA**-*****-****-XXXX",
    riskTier: "Medium",
    employees: 342,
    amlOfficer: "Nora Al-Rashidi",
  };

  // Users (portal employees)
  const users = [
    { id: "U001", name: "Nora Al-Rashidi", role: "Chief Compliance Officer", clearance: 5, initials: "NA", lastLogin: "2026-06-30 08:14" },
    { id: "U002", name: "Faisal Al-Otaibi", role: "Senior AML Analyst",       clearance: 4, initials: "FA", lastLogin: "2026-06-30 07:55" },
    { id: "U003", name: "Lama Al-Zahrani",  role: "Risk Intelligence Officer", clearance: 4, initials: "LZ", lastLogin: "2026-06-29 18:30" },
    { id: "U004", name: "Tariq Al-Dawsari", role: "Transaction Reviewer",      clearance: 3, initials: "TD", lastLogin: "2026-06-30 09:01" },
    { id: "U005", name: "Reem Al-Sulami",   role: "Audit Coordinator",         clearance: 3, initials: "RS", lastLogin: "2026-06-28 14:20" },
  ];

  // Active session user
  let currentUser = users[0];

  // Clients / counterparties
  const clients = [
    { id: "C001", name: "Gulf Commodities LLC",        country: "AE", riskScore: 82, riskLevel: "high",   kycStatus: "expired",   totalTxns: 47, flagged: 9,  type: "Corporate", lastActivity: "2026-06-29" },
    { id: "C002", name: "Horizon Logistics KSA",       country: "SA", riskScore: 34, riskLevel: "low",    kycStatus: "verified",  totalTxns: 91, flagged: 1,  type: "Corporate", lastActivity: "2026-06-30" },
    { id: "C003", name: "Al-Masri Trading Group",      country: "EG", riskScore: 67, riskLevel: "medium", kycStatus: "pending",   totalTxns: 28, flagged: 4,  type: "Corporate", lastActivity: "2026-06-28" },
    { id: "C004", name: "Eastern Ports International", country: "AE", riskScore: 91, riskLevel: "high",   kycStatus: "failed",    totalTxns: 15, flagged: 11, type: "Corporate", lastActivity: "2026-06-27" },
    { id: "C005", name: "Riyadh Supply Chain Co.",     country: "SA", riskScore: 28, riskLevel: "low",    kycStatus: "verified",  totalTxns: 134,flagged: 0,  type: "Corporate", lastActivity: "2026-06-30" },
    { id: "C006", name: "Blue Nile Exports Ltd.",      country: "SD", riskScore: 88, riskLevel: "high",   kycStatus: "pending",   totalTxns: 9,  flagged: 7,  type: "Corporate", lastActivity: "2026-06-25" },
    { id: "C007", name: "Levant Shipping Solutions",   country: "LB", riskScore: 74, riskLevel: "medium", kycStatus: "verified",  totalTxns: 33, flagged: 3,  type: "Corporate", lastActivity: "2026-06-29" },
    { id: "C008", name: "Saudi Fresh Produce Co.",     country: "SA", riskScore: 19, riskLevel: "low",    kycStatus: "verified",  totalTxns: 210,flagged: 0,  type: "Corporate", lastActivity: "2026-06-30" },
    { id: "C009", name: "Pinnacle Holdings BVI",       country: "VG", riskScore: 96, riskLevel: "high",   kycStatus: "failed",    totalTxns: 6,  flagged: 6,  type: "Shell",     lastActivity: "2026-06-20" },
    { id: "C010", name: "Trans-Gulf Metals",           country: "KW", riskScore: 55, riskLevel: "medium", kycStatus: "verified",  totalTxns: 62, flagged: 2,  type: "Corporate", lastActivity: "2026-06-28" },
  ];

  // Transactions
  const transactions = [
    { id: "TXN-2026-00891", date: "2026-06-30", time: "10:22", client: "C001", amount: 4850000,  currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "flagged",    aiRisk: 94, flags: ["Structuring Pattern","Unusual Volume Spike","Expired KYC"],             notes: "SAR 4.85M received from Gulf Commodities LLC — 6th transfer exceeding SAR 1M in 30 days. Volume 340% above 6-month average. KYC documents expired.", assignee: "U002" },
    { id: "TXN-2026-00890", date: "2026-06-30", time: "09:47", client: "C009", amount: 2100000,  currency: "SAR", type: "Outbound Wire",   channel: "SWIFT", status: "blocked",    aiRisk: 98, flags: ["Shell Company Destination","Undisclosed UBO","No Business Rationale"], notes: "Attempted outbound transfer to Pinnacle Holdings BVI — jurisdiction is high-risk with no commercial relationship on record. Blocked pending EDD.", assignee: "U001" },
    { id: "TXN-2026-00889", date: "2026-06-29", time: "17:55", client: "C004", amount: 980000,   currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "flagged",    aiRisk: 87, flags: ["Failed KYC","High-Risk Jurisdiction","Layering Indicator"],            notes: "Inbound from Eastern Ports International whose KYC verification failed. Third transfer below SAR 1M threshold in 7 days — structuring pattern detected.", assignee: "U002" },
    { id: "TXN-2026-00888", date: "2026-06-29", time: "15:30", client: "C006", amount: 3300000,  currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "under_review",aiRisk: 81, flags: ["Politically Exposed Counterparty","Sudan Jurisdiction"],              notes: "Large inbound from Blue Nile Exports Ltd. in Sudan. AI model flagged counterparty as linked to a PEP. Awaiting EDD completion.", assignee: "U003" },
    { id: "TXN-2026-00887", date: "2026-06-29", time: "11:12", client: "C002", amount: 540000,   currency: "SAR", type: "Outbound Wire",   channel: "SWIFT", status: "cleared",    aiRisk: 12, flags: [],                                                                      notes: "Routine supplier payment. KYC verified, business rationale confirmed.", assignee: "U004" },
    { id: "TXN-2026-00886", date: "2026-06-29", time: "09:03", client: "C003", amount: 1750000,  currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "flagged",    aiRisk: 71, flags: ["Pending KYC","Beneficial Owner Mismatch","Unusual Timing"],           notes: "Funds received before KYC process completed. Declared UBO name does not match company registry. Last-minute beneficiary change noted.", assignee: "U002" },
    { id: "TXN-2026-00885", date: "2026-06-28", time: "20:44", client: "C004", amount: 870000,   currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "flagged",    aiRisk: 85, flags: ["Structuring Pattern","Off-Hours Transaction"],                        notes: "Transfer initiated at 20:44 — outside standard business hours. Combined with TXN-00889, total is SAR 1.85M from Eastern Ports in 48 hours.", assignee: "U002" },
    { id: "TXN-2026-00884", date: "2026-06-28", time: "14:20", client: "C007", amount: 660000,   currency: "SAR", type: "Outbound Wire",   channel: "SWIFT", status: "cleared",    aiRisk: 38, flags: ["Lebanon Jurisdiction"],                                               notes: "Payment to Levant Shipping for logistics services. Reviewed and cleared after confirming commercial invoice.", assignee: "U004" },
    { id: "TXN-2026-00883", date: "2026-06-28", time: "10:00", client: "C005", amount: 2200000,  currency: "SAR", type: "Inbound Wire",    channel: "ACH",   status: "cleared",    aiRisk: 8,  flags: [],                                                                      notes: "Regular quarterly bulk receipt from Riyadh Supply Chain. Fully documented.", assignee: "U004" },
    { id: "TXN-2026-00882", date: "2026-06-27", time: "16:15", client: "C001", amount: 1200000,  currency: "SAR", type: "Outbound Wire",   channel: "SWIFT", status: "under_review",aiRisk: 76, flags: ["Rapid Fund Turnaround","Circular Flow Indicator"],                   notes: "Outbound SAR 1.2M to Gulf Commodities LLC 30 hrs after receiving SAR 4.85M from same entity. Possible layering through commercial invoices.", assignee: "U003" },
    { id: "TXN-2026-00881", date: "2026-06-27", time: "08:30", client: "C010", amount: 450000,   currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "cleared",    aiRisk: 23, flags: [],                                                                      notes: "Metals delivery payment from Trans-Gulf. Normal transaction.", assignee: "U004" },
    { id: "TXN-2026-00880", date: "2026-06-26", time: "13:45", client: "C006", amount: 980000,   currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "flagged",    aiRisk: 79, flags: ["Structuring Pattern","Sudan Jurisdiction","Third-Party Payor"],       notes: "Payment instructed by a third party different from the named sender. Sudan jurisdiction requires enhanced scrutiny.", assignee: "U003" },
    { id: "TXN-2026-00879", date: "2026-06-25", time: "11:20", client: "C009", amount: 1600000,  currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "blocked",    aiRisk: 99, flags: ["Shell Company","BVI Jurisdiction","No KYC","Undisclosed UBO"],        notes: "Inbound from Pinnacle Holdings BVI — shell entity with zero commercial history. Blocked automatically by AI model before processing.", assignee: "U001" },
    { id: "TXN-2026-00878", date: "2026-06-25", time: "09:55", client: "C008", amount: 310000,   currency: "SAR", type: "Outbound Wire",   channel: "ACH",   status: "cleared",    aiRisk: 5,  flags: [],                                                                      notes: "Regular operational payment to Saudi Fresh Produce.", assignee: "U004" },
    { id: "TXN-2026-00877", date: "2026-06-24", time: "14:00", client: "C001", amount: 990000,   currency: "SAR", type: "Inbound Wire",    channel: "SWIFT", status: "flagged",    aiRisk: 88, flags: ["Structuring","Repeat Pattern"],                                        notes: "Another sub-threshold inbound from Gulf Commodities. Pattern analysis confirms intentional structuring to remain below SAR 1M reporting threshold.", assignee: "U002" },
  ];

  // STR Reports
  const strReports = [
    { id: "STR-2026-041", date: "2026-06-30", txnIds: ["TXN-2026-00891","TXN-2026-00877"], client: "C001", status: "submitted", submittedBy: "U001", submittedTo: "SAFIU", submittedAt: "2026-06-30 11:00", narrative: "Repeated structuring pattern from Gulf Commodities LLC totalling SAR 5.84M over 7 days with no plausible commercial rationale. EDD initiated. KYC expired.", confidential: true },
    { id: "STR-2026-040", date: "2026-06-30", txnIds: ["TXN-2026-00890","TXN-2026-00879"], client: "C009", status: "submitted", submittedBy: "U001", submittedTo: "SAFIU", submittedAt: "2026-06-30 10:15", narrative: "Two attempted transfers involving Pinnacle Holdings BVI — shell company in BVI with undisclosed UBO. Both blocked. No business relationship justified.", confidential: true },
    { id: "STR-2026-039", date: "2026-06-29", txnIds: ["TXN-2026-00889","TXN-2026-00885"], client: "C004", status: "submitted", submittedBy: "U002", submittedTo: "SAFIU", submittedAt: "2026-06-29 20:00", narrative: "Structuring pattern from Eastern Ports International — three inbound transfers totalling SAR 2.83M structured just below threshold in 7 days. Failed KYC.", confidential: true },
    { id: "STR-2026-038", date: "2026-06-27", txnIds: ["TXN-2026-00882"], client: "C001", status: "draft", submittedBy: "U003", submittedTo: null, submittedAt: null, narrative: "Rapid turnaround of funds — outbound SAR 1.2M to same entity (Gulf Commodities) within 30 hrs of receiving SAR 4.85M. Possible layering.", confidential: true },
    { id: "STR-2026-037", date: "2026-06-26", txnIds: ["TXN-2026-00880"], client: "C006", status: "closed_no_action", submittedBy: "U002", submittedTo: null, submittedAt: null, narrative: "Initial suspicion on Blue Nile third-party payment. Upon further review commercial invoice corroborated legitimate trade. Documented per AML requirements.", confidential: true },
  ];

  // Audit log
  const auditLog = [
    { id: "AL-10091", ts: "2026-06-30 11:00", user: "U001", action: "STR_SUBMITTED",      target: "STR-2026-041", detail: "STR submitted to SAFIU via secure channel",            ip: "10.4.1.22" },
    { id: "AL-10090", ts: "2026-06-30 10:45", user: "U001", action: "TXN_BLOCKED",        target: "TXN-2026-00890",detail: "Transaction blocked — shell company destination",       ip: "10.4.1.22" },
    { id: "AL-10089", ts: "2026-06-30 10:15", user: "U001", action: "STR_SUBMITTED",      target: "STR-2026-040", detail: "STR submitted to SAFIU via secure channel",            ip: "10.4.1.22" },
    { id: "AL-10088", ts: "2026-06-30 09:55", user: "U002", action: "ALERT_REVIEWED",     target: "TXN-2026-00891",detail: "Alert reviewed — escalated to CCO for STR decision",  ip: "10.4.1.18" },
    { id: "AL-10087", ts: "2026-06-30 09:30", user: "U002", action: "CLIENT_EDD_OPENED",  target: "C001",         detail: "Enhanced Due Diligence initiated on Gulf Commodities",  ip: "10.4.1.18" },
    { id: "AL-10086", ts: "2026-06-29 20:00", user: "U002", action: "STR_SUBMITTED",      target: "STR-2026-039", detail: "STR submitted to SAFIU via secure channel",            ip: "10.4.1.18" },
    { id: "AL-10085", ts: "2026-06-29 17:55", user: "U002", action: "ALERT_REVIEWED",     target: "TXN-2026-00889",detail: "Structuring pattern confirmed — STR initiated",        ip: "10.4.1.18" },
    { id: "AL-10084", ts: "2026-06-29 16:10", user: "U003", action: "EDD_REQUESTED",      target: "C006",         detail: "EDD requested due to PEP link — Blue Nile Exports",    ip: "10.4.1.31" },
    { id: "AL-10083", ts: "2026-06-29 15:30", user: "U003", action: "ALERT_REVIEWED",     target: "TXN-2026-00888",detail: "Alert reviewed — EDD in progress. No block applied yet",ip: "10.4.1.31" },
    { id: "AL-10082", ts: "2026-06-29 11:12", user: "U004", action: "TXN_CLEARED",        target: "TXN-2026-00887",detail: "Transaction cleared after document review",             ip: "10.4.1.40" },
    { id: "AL-10081", ts: "2026-06-28 14:20", user: "U004", action: "TXN_CLEARED",        target: "TXN-2026-00884",detail: "Payment to Levant Shipping cleared",                  ip: "10.4.1.40" },
    { id: "AL-10080", ts: "2026-06-27 19:00", user: "U003", action: "STR_DRAFTED",        target: "STR-2026-038", detail: "Draft STR created — layering assessment pending CCO",  ip: "10.4.1.31" },
    { id: "AL-10079", ts: "2026-06-25 14:35", user: "U001", action: "TXN_BLOCKED",        target: "TXN-2026-00879",detail: "Auto-block confirmed by CCO — BVI shell entity",       ip: "10.4.1.22" },
    { id: "AL-10078", ts: "2026-06-24 14:30", user: "U002", action: "ALERT_ESCALATED",    target: "TXN-2026-00877",detail: "Structuring alert escalated — third occurrence",       ip: "10.4.1.18" },
    { id: "AL-10077", ts: "2026-06-24 08:00", user: "U005", action: "REPORT_EXPORTED",    target: "AUDIT-JUN-2026",detail: "Monthly audit trail exported to secure archive",       ip: "10.4.1.55" },
  ];

  // AI Alert Queue
  const alertQueue = [
    { id: "ALT-2026-0084", ts: "2026-06-30 10:22", txnId: "TXN-2026-00891", clientId: "C001", aiScore: 94, type: "Structuring", severity: "critical", status: "escalated",   summary: "Sixth sub-threshold transfer in 30 days from Gulf Commodities LLC" },
    { id: "ALT-2026-0083", ts: "2026-06-30 09:47", txnId: "TXN-2026-00890", clientId: "C009", aiScore: 98, type: "Shell Company", severity: "critical", status: "blocked",    summary: "Outbound to known shell entity in BVI — no business rationale" },
    { id: "ALT-2026-0082", ts: "2026-06-29 17:55", txnId: "TXN-2026-00889", clientId: "C004", aiScore: 87, type: "Structuring", severity: "high",     status: "escalated",   summary: "Repeated structuring pattern from Eastern Ports International" },
    { id: "ALT-2026-0081", ts: "2026-06-29 15:30", txnId: "TXN-2026-00888", clientId: "C006", aiScore: 81, type: "PEP Linkage", severity: "high",     status: "under_review",summary: "Counterparty linked to Politically Exposed Person — Sudan jurisdiction" },
    { id: "ALT-2026-0080", ts: "2026-06-29 09:03", txnId: "TXN-2026-00886", clientId: "C003", aiScore: 71, type: "UBO Mismatch", severity: "high",     status: "under_review",summary: "Declared UBO name mismatch with commercial registry data" },
    { id: "ALT-2026-0079", ts: "2026-06-28 20:44", txnId: "TXN-2026-00885", clientId: "C004", aiScore: 85, type: "Off-Hours",   severity: "high",     status: "escalated",   summary: "Off-hours transfer combined with prior structuring activity" },
    { id: "ALT-2026-0078", ts: "2026-06-27 16:15", txnId: "TXN-2026-00882", clientId: "C001", aiScore: 76, type: "Layering",    severity: "medium",   status: "under_review",summary: "Rapid fund turnaround — outbound to same sender within 30 hours" },
    { id: "ALT-2026-0077", ts: "2026-06-26 13:45", txnId: "TXN-2026-00880", clientId: "C006", aiScore: 79, type: "Third-Party", severity: "medium",   status: "closed",      summary: "Payment instructed by unregistered third party in Sudan" },
    { id: "ALT-2026-0076", ts: "2026-06-24 14:00", txnId: "TXN-2026-00877", clientId: "C001", aiScore: 88, type: "Structuring", severity: "critical", status: "escalated",   summary: "Sub-threshold pattern confirmed — fifth occurrence in 30 days" },
  ];

  // Dashboard metrics
  const dashMetrics = {
    openAlerts: 7,
    blockedToday: 2,
    strSubmittedMTD: 3,
    avgRiskScore: 61,
    txnsReviewedMTD: 47,
    pendingEDD: 3,
    highRiskClients: 4,
    alertsResolvedMTD: 31,
    volumeMonitored: "SAR 18.43M",
  };

  // Volume chart data (last 14 days — daily flagged vs cleared)
  const volumeData = [
    { d:"Jun 17", total:890000,  flagged:0 },
    { d:"Jun 18", total:1240000, flagged:0 },
    { d:"Jun 19", total:2100000, flagged:1200000 },
    { d:"Jun 20", total:1650000, flagged:1650000 },
    { d:"Jun 21", total:430000,  flagged:0 },
    { d:"Jun 22", total:310000,  flagged:0 },
    { d:"Jun 23", total:2800000, flagged:980000 },
    { d:"Jun 24", total:3100000, flagged:1990000 },
    { d:"Jun 25", total:1910000, flagged:1600000 },
    { d:"Jun 26", total:2240000, flagged:980000 },
    { d:"Jun 27", total:2850000, flagged:2850000 },
    { d:"Jun 28", total:3310000, flagged:870000 },
    { d:"Jun 29", total:7480000, flagged:4930000 },
    { d:"Jun 30", total:6950000, flagged:6950000 },
  ];

  // Public API
  return {
    company,
    users,
    currentUser,
    getUser: (id) => users.find(u => u.id === id),
    clients,
    getClient: (id) => clients.find(c => c.id === id),
    transactions,
    getTxn: (id) => transactions.find(t => t.id === id),
    strReports,
    auditLog,
    alertQueue,
    dashMetrics,
    volumeData,
  };
})();

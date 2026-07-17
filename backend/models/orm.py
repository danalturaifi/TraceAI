from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base
import enum

class ClearanceLevel(int, enum.Enum):
    reviewer = 3
    risk_officer = 4
    senior_aml = 4
    cco = 5

class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class TxnStatus(str, enum.Enum):
    cleared = "cleared"
    flagged = "flagged"
    blocked = "blocked"
    under_review = "under_review"

class STRStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    closed_no_action = "closed_no_action"

class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True)
    name          = Column(String, nullable=False)
    role          = Column(String, nullable=False)
    clearance     = Column(Integer, nullable=False)
    hashed_pin    = Column(String, nullable=False)
    is_active     = Column(Boolean, default=True)
    failed_logins = Column(Integer, default=0)
    locked_until  = Column(DateTime, nullable=True)
    last_login    = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, server_default=func.now())

    audit_entries = relationship("AuditLog", back_populates="user")

class Client(Base):
    __tablename__ = "clients"
    id            = Column(String, primary_key=True)
    name          = Column(String, nullable=False)
    country       = Column(String(2), nullable=False)
    entity_type   = Column(String, default="Corporate")
    risk_score    = Column(Integer, nullable=False)
    risk_level    = Column(String, nullable=False)
    kyc_status    = Column(String, nullable=False)
    kyc_expiry    = Column(DateTime, nullable=True)
    ubo_name      = Column(String, nullable=True)
    is_pep        = Column(Boolean, default=False)
    is_shell      = Column(Boolean, default=False)
    total_txns    = Column(Integer, default=0)
    flagged_txns  = Column(Integer, default=0)
    last_activity = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, server_default=func.now())

    transactions  = relationship("Transaction", back_populates="client")

class Transaction(Base):
    __tablename__ = "transactions"
    id            = Column(String, primary_key=True)
    client_id     = Column(String, ForeignKey("clients.id"), nullable=False)
    amount        = Column(Float, nullable=False)
    currency      = Column(String(3), default="SAR")
    txn_type      = Column(String, nullable=False)
    channel       = Column(String, nullable=False)
    status        = Column(String, default="flagged")
    ai_risk_score = Column(Float, nullable=True)
    flags         = Column(Text, default="[]")   # JSON list stored as text
    notes         = Column(Text, nullable=True)
    assignee_id   = Column(String, ForeignKey("users.id"), nullable=True)
    txn_date      = Column(DateTime, nullable=False)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, onupdate=func.now())

    client        = relationship("Client", back_populates="transactions")
    alerts        = relationship("AIAlert", back_populates="transaction")

class AIAlert(Base):
    __tablename__ = "ai_alerts"
    id            = Column(String, primary_key=True)
    txn_id        = Column(String, ForeignKey("transactions.id"), nullable=False)
    client_id     = Column(String, ForeignKey("clients.id"), nullable=False)
    ai_score      = Column(Float, nullable=False)
    pattern_type  = Column(String, nullable=False)
    severity      = Column(String, nullable=False)
    status        = Column(String, default="open")
    summary       = Column(Text)
    shap_values   = Column(Text, nullable=True)   # JSON
    created_at    = Column(DateTime, server_default=func.now())

    transaction   = relationship("Transaction", back_populates="alerts")

class STRReport(Base):
    __tablename__ = "str_reports"
    id            = Column(String, primary_key=True)
    client_id     = Column(String, ForeignKey("clients.id"), nullable=False)
    txn_ids       = Column(Text, nullable=False)  # JSON list
    narrative     = Column(Text, nullable=False)
    status        = Column(String, default="draft")
    submitted_by  = Column(String, ForeignKey("users.id"), nullable=False)
    submitted_to  = Column(String, nullable=True)
    submitted_at  = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_log"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    event_id      = Column(String, unique=True, nullable=False)
    user_id       = Column(String, ForeignKey("users.id"), nullable=False)
    action        = Column(String, nullable=False)
    target        = Column(String, nullable=True)
    detail        = Column(Text, nullable=True)
    ip_address    = Column(String, nullable=True)
    user_agent    = Column(String, nullable=True)
    created_at    = Column(DateTime, server_default=func.now())

    user          = relationship("User", back_populates="audit_entries")

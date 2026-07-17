"""
TraceAI v2 — FastAPI Backend
Entry point. Run with: uvicorn main:app --reload
"""
import logging
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from config import get_settings
from db.database import engine, get_db, Base
from models.orm import User, AuditLog
from middleware.audit import AuditMiddleware, write_audit_event
from middleware.auth import create_access_token, get_current_user, require_reviewer
from routers.analysis import router as analysis_router

# ── Bootstrap ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger   = logging.getLogger("traceai.main")
settings = get_settings()
pwd_ctx  = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,   # disable Swagger in prod
    redoc_url=None,
)

# ── Middleware ──────────────────────────────────────────────────────────────
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://danalturaifi.github.io"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",  # your GitHub Pages domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["*"],
)

# Security headers on every response
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-Frame-Options"]           = "DENY"
    response.headers["X-XSS-Protection"]          = "1; mode=block"
    response.headers["Referrer-Policy"]           = "strict-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(analysis_router)

# ── Auth endpoints ──────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    user_id: str
    pin: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@app.post("/api/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == body.user_id, User.is_active == True).first()

    # Account lockout check
    if user and user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked. Try again in {remaining} minutes.",
        )

    if not user or not pwd_ctx.verify(body.pin, user.hashed_pin):
        if user:
            user.failed_logins = (user.failed_logins or 0) + 1
            if user.failed_logins >= settings.max_login_attempts:
                user.locked_until = datetime.utcnow() + timedelta(minutes=settings.lockout_minutes)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Successful login
    user.failed_logins = 0
    user.locked_until  = None
    user.last_login    = datetime.utcnow()
    db.commit()

    write_audit_event(db, user.id, "USER_LOGIN", user.id,
                      "Successful login", request.client.host if request.client else "unknown")

    token = create_access_token({
        "sub":       user.id,
        "name":      user.name,
        "role":      user.role,
        "clearance": user.clearance,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id":        user.id,
            "name":      user.name,
            "role":      user.role,
            "clearance": user.clearance,
        },
    )

@app.post("/api/auth/logout", tags=["Auth"])
def logout(request: Request, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    write_audit_event(db, user["sub"], "USER_LOGOUT", user["sub"],
                      "User logged out", request.client.host if request.client else "unknown")
    return {"message": "Logged out"}

# ── Health ──────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
def health():
    return {"status": "ok", "version": settings.app_version, "time": datetime.utcnow().isoformat()}

# ── Audit export (CCO only via token validation in prod) ────────────────────
@app.get("/api/audit", tags=["Audit"])
def get_audit_log(
    limit: int = 100,
    db: Session  = Depends(get_db),
    user: dict   = Depends(require_reviewer),
):
    if user.get("clearance", 0) < 3:
        raise HTTPException(status_code=403, detail="Insufficient clearance")
    entries = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    return [
        {
            "event_id":  e.event_id,
            "timestamp": e.created_at.isoformat() if e.created_at else None,
            "user_id":   e.user_id,
            "action":    e.action,
            "target":    e.target,
            "detail":    e.detail,
            "ip":        e.ip_address,
        }
        for e in entries
    ]

# ── Demo data seeding (portal login users) ───────────────────────────────────
from seed import seed_demo_users
seed_demo_users()

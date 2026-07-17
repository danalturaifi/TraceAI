"""
Immutable Audit Trail Middleware
Every state-changing request is logged automatically.
Logs cannot be deleted — only exported (read-only endpoint).
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import uuid, logging, json
from datetime import datetime

logger = logging.getLogger("traceai.audit")

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SKIP_PATHS      = {"/api/auth/login", "/api/health", "/docs", "/openapi.json"}

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if request.method in AUDITED_METHODS and request.url.path not in SKIP_PATHS:
            user = getattr(request.state, "user", {})
            logger.info(json.dumps({
                "event_id":   f"AL-{uuid.uuid4().hex[:8].upper()}",
                "timestamp":  datetime.utcnow().isoformat(),
                "user_id":    user.get("sub", "anonymous"),
                "method":     request.method,
                "path":       request.url.path,
                "status":     response.status_code,
                "ip":         request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
            }))

        return response


def write_audit_event(db, user_id: str, action: str, target: str,
                      detail: str, ip: str = "system") -> None:
    """Write a named audit event directly to DB (used by routers)."""
    from models.orm import AuditLog
    entry = AuditLog(
        event_id  =f"AL-{uuid.uuid4().hex[:8].upper()}",
        user_id   =user_id,
        action    =action,
        target    =target,
        detail    =detail,
        ip_address=ip,
    )
    db.add(entry)
    db.commit()

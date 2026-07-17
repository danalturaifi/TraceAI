"""
JWT Authentication + Clearance-Level RBAC
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from config import get_settings

settings     = get_settings()
oauth2_scheme= OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire  = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)

def require_clearance(level: int):
    """Dependency factory: require minimum clearance level."""
    def _check(user: dict = Depends(get_current_user)):
        if user.get("clearance", 0) < level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Clearance level {level} required. Your level: {user.get('clearance')}",
            )
        return user
    return _check

# Shorthand dependencies
require_cco     = require_clearance(5)
require_analyst = require_clearance(4)
require_reviewer= require_clearance(3)

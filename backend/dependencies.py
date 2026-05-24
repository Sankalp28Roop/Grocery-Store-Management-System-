"""
dependencies.py — Reusable FastAPI dependency injection helpers.

Provides current_user extraction from Bearer tokens, role-guard factories,
and common query parameter dependencies.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.auth import decode_access_token
from backend.database import get_db
from backend.models import User, UserRole


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def _extract_token(authorization: Optional[str] = Header(default=None)) -> str:
    """Extract Bearer token from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1]


# ---------------------------------------------------------------------------
# Current user dependency
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(_extract_token),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate JWT and return the authenticated User ORM instance.

    Raises 401 if the token is invalid/expired.
    Raises 403 if the user account is deactivated.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exc

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exc

    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_exc
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


# ---------------------------------------------------------------------------
# Role-based guards
# ---------------------------------------------------------------------------

def _require_roles(*roles: UserRole):
    """Factory that returns a FastAPI dependency enforcing role membership."""

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[r.value for r in roles]}",
            )
        return current_user

    return _guard


require_admin = _require_roles(UserRole.admin)
require_manager_or_above = _require_roles(UserRole.admin, UserRole.manager)
require_cashier_or_above = _require_roles(UserRole.admin, UserRole.manager, UserRole.cashier)


# ---------------------------------------------------------------------------
# Pagination dependency
# ---------------------------------------------------------------------------

def pagination(
    skip: int = Query(default=0, ge=0, description="Records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
) -> dict:
    return {"skip": skip, "limit": limit}

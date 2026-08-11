from datetime import datetime, timezone

from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import DomainError
from app.models import AthleteProfile, AuthSession, User
from app.security import token_digest


def current_user(
    athleteos_session: str | None = Cookie(default=None), db: Session = Depends(get_db)
) -> User:
    if not athleteos_session:
        raise DomainError("AUTH_REQUIRED", "Please sign in to continue.", 401)
    auth_session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == token_digest(athleteos_session))
    )
    now = datetime.now(timezone.utc)
    if not auth_session or auth_session.revoked_at is not None:
        raise DomainError("SESSION_EXPIRED", "Your session has expired. Please sign in again.", 401)
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise DomainError("SESSION_EXPIRED", "Your session has expired. Please sign in again.", 401)
    user = db.get(User, auth_session.user_id)
    if not user or user.status != "active":
        raise DomainError("ACCOUNT_UNAVAILABLE", "This account is unavailable.", 401)
    return user


def current_profile(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> AthleteProfile:
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    if not profile:
        raise DomainError("PROFILE_NOT_FOUND", "Athlete profile was not found.", 404)
    return profile


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role not in {"content_admin", "ops_admin"}:
        raise DomainError("FORBIDDEN", "Administrator access is required.", 403)
    return user

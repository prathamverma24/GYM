import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.dependencies import current_user
from app.errors import DomainError
from app.models import (
    AthleteProfile,
    AuditEvent,
    AuthSession,
    Consent,
    PasswordResetToken,
    User,
    utcnow,
)
from app.security import hash_password, new_token, token_digest, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    confirm_password: str
    accept_terms: bool

    @model_validator(mode="after")
    def validate_registration(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        if not self.accept_terms:
            raise ValueError("Terms and Privacy acceptance is required")
        if not re.search(r"[A-Z]", self.password) or not re.search(r"\d", self.password):
            raise ValueError("Password needs an uppercase letter and a number")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    token: str
    password: str = Field(min_length=10, max_length=128)


def public_user(user: User, profile: AthleteProfile | None) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "first_name": user.full_name.split()[0],
        "role": user.role,
        "timezone": user.timezone,
        "onboarding_completed": bool(profile and profile.onboarding_completed),
        "onboarding_step": profile.onboarding_step if profile else 1,
        "experience_level": profile.experience_level if profile else None,
    }


def set_session(db: Session, response: Response, user: User) -> None:
    token = new_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    db.add(AuthSession(user_id=user.id, token_hash=token_digest(token), expires_at=expires))
    db.commit()
    response.set_cookie(
        "athleteos_session",
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise DomainError("EMAIL_UNAVAILABLE", "An account with this email already exists.", 409)
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    profile = AthleteProfile(user_id=user.id)
    db.add(profile)
    db.add(Consent(user_id=user.id, consent_type="terms", version="1.0", granted_at=utcnow()))
    db.add(Consent(user_id=user.id, consent_type="privacy", version="1.0", granted_at=utcnow()))
    db.add(
        AuditEvent(
            actor_user_id=user.id,
            action="account.registered",
            entity_type="user",
            entity_id=user.id,
            request_id=getattr(request.state, "request_id", None),
        )
    )
    db.commit()
    set_session(db, response, user)
    return {"user": public_user(user, profile)}


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise DomainError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    set_session(db, response, user)
    return {"user": public_user(user, profile)}


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    athleteos_session: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Revoke every session with the supplied cookie through the dependency-resolved user.
    # Device-level controls can expose individual session IDs in a later hardening phase.
    sessions = db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    ).all()
    for session in sessions:
        session.revoked_at = utcnow()
    db.commit()
    response.delete_cookie("athleteos_session", path="/")


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    return {"user": public_user(user, profile)}


@router.post("/forgot-password")
def forgot_password(payload: ForgotRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    debug_token = None
    if user:
        token = new_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_digest(token),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            )
        )
        db.commit()
        if settings.app_env in {"development", "test"}:
            debug_token = token
    response = {"message": "If an account exists, password reset instructions have been sent."}
    if debug_token:
        response["development_reset_token"] = debug_token
    return response


@router.post("/reset-password")
def reset_password(payload: ResetRequest, db: Session = Depends(get_db)):
    reset = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_digest(payload.token))
    )
    if not reset or reset.used_at:
        raise DomainError("RESET_TOKEN_INVALID", "This reset link is invalid or already used.", 400)
    expires = reset.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        raise DomainError("RESET_TOKEN_EXPIRED", "This reset link has expired.", 400)
    user = db.get(User, reset.user_id)
    if not user:
        raise DomainError("RESET_TOKEN_INVALID", "This reset link is invalid.", 400)
    user.password_hash = hash_password(payload.password)
    reset.used_at = utcnow()
    for session in db.scalars(select(AuthSession).where(AuthSession.user_id == user.id)).all():
        session.revoked_at = utcnow()
    db.commit()
    return {"message": "Password updated. Please sign in again."}


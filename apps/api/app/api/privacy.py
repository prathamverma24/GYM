from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_profile, current_user
from app.errors import DomainError
from app.models import (
    AthleteProfile,
    AuthSession,
    BodyMetricEntry,
    Consent,
    CvAssessment,
    Habit,
    MealLog,
    User,
    WorkoutSession,
    utcnow,
)

router = APIRouter(tags=["privacy"])


class ConsentRequest(BaseModel):
    granted: bool
    version: str = "1.0"


@router.get("/privacy/consents")
def consent_state(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Consent).where(Consent.user_id == user.id)).all()
    return {"items": [{"type": row.consent_type, "version": row.version, "granted_at": row.granted_at, "revoked_at": row.revoked_at, "granted": bool(row.granted_at and not row.revoked_at)} for row in rows]}


@router.put("/privacy/consents/{consent_type}")
def update_consent(consent_type: str, payload: ConsentRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if consent_type in {"terms", "privacy"} and not payload.granted:
        raise DomainError("REQUIRED_CONSENT", "Required account consent can only be withdrawn through account deletion.", 409)
    if consent_type not in {"cv_processing", "raw_photo_storage", "analytics", "research"}:
        raise DomainError("INVALID_CONSENT_TYPE", "Unsupported consent type.")
    row = db.scalar(select(Consent).where(Consent.user_id == user.id, Consent.consent_type == consent_type))
    if not row:
        row = Consent(user_id=user.id, consent_type=consent_type, version=payload.version)
        db.add(row)
    row.version = payload.version
    if payload.granted:
        row.granted_at = utcnow()
        row.revoked_at = None
    else:
        row.revoked_at = utcnow()
    db.commit()
    return {"type": consent_type, "granted": payload.granted, "media_deletion_queued": not payload.granted and consent_type == "raw_photo_storage"}


@router.get("/account/export")
def export_account(user: User = Depends(current_user), profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    return {
        "generated_at": datetime.now(timezone.utc),
        "account": {"id": user.id, "email": user.email, "full_name": user.full_name, "timezone": user.timezone},
        "profile": {"training_type": profile.training_type, "experience_level": profile.experience_level, "primary_goal": profile.primary_goal, "equipment": profile.equipment, "schedule": profile.schedule},
        "record_counts": {
            "body_metrics": db.scalar(select(func.count()).select_from(BodyMetricEntry).where(BodyMetricEntry.athlete_id == profile.id)),
            "workouts": db.scalar(select(func.count()).select_from(WorkoutSession).where(WorkoutSession.athlete_id == profile.id)),
            "meals": db.scalar(select(func.count()).select_from(MealLog).where(MealLog.athlete_id == profile.id)),
            "habits": db.scalar(select(func.count()).select_from(Habit).where(Habit.athlete_id == profile.id)),
            "cv_assessments": db.scalar(select(func.count()).select_from(CvAssessment).where(CvAssessment.athlete_id == profile.id)),
        },
        "note": "This synchronous MVP export contains account metadata and record counts. A production export job will include full machine-readable histories in a short-lived encrypted archive.",
    }


@router.delete("/account", status_code=202)
def request_account_deletion(response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.status = "pending_deletion"
    for auth_session in db.scalars(select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))).all():
        auth_session.revoked_at = utcnow()
    db.commit()
    response.delete_cookie("athleteos_session", path="/")
    return {"status": "pending_deletion", "message": "Account deletion was queued. Production workers must purge or anonymize data according to the configured retention policy."}


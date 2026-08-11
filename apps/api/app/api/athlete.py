from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_profile, current_user
from app.domains.readiness import calculate_readiness
from app.domains.training import generate_program
from app.errors import DomainError
from app.models import AthleteProfile, BodyMetricEntry, Consent, ReadinessLog, User, utcnow

router = APIRouter(tags=["athlete"])


class OnboardingPayload(BaseModel):
    step: int = Field(ge=1, le=9)
    data: dict


class MetricPayload(BaseModel):
    weight_kg: float | None = Field(default=None, gt=25, lt=400)
    chest_cm: float | None = Field(default=None, gt=30, lt=250)
    waist_cm: float | None = Field(default=None, gt=30, lt=250)
    shoulders_cm: float | None = Field(default=None, gt=30, lt=250)
    arms_cm: float | None = Field(default=None, gt=10, lt=100)
    thighs_cm: float | None = Field(default=None, gt=15, lt=150)
    hips_cm: float | None = Field(default=None, gt=30, lt=250)
    neck_cm: float | None = Field(default=None, gt=15, lt=100)
    measured_at: datetime | None = None
    source: str = "manual"


class ReadinessPayload(BaseModel):
    sleep_hours: float | None = Field(default=None, ge=0, le=16)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    soreness: int | None = Field(default=None, ge=1, le=5)
    energy: int | None = Field(default=None, ge=1, le=5)
    motivation: int | None = Field(default=None, ge=1, le=5)
    stress: int | None = Field(default=None, ge=1, le=5)
    resting_heart_rate: int | None = Field(default=None, ge=30, le=220)


def profile_payload(profile: AthleteProfile, db: Session | None = None) -> dict:
    payload = {
        "id": profile.id,
        "date_of_birth": profile.date_of_birth,
        "height_cm": profile.height_cm,
        "unit_system": profile.unit_system,
        "country": profile.country,
        "gender": profile.gender,
        "activity_level": profile.activity_level,
        "sleep_hours": profile.sleep_hours,
        "water_target_ml": profile.water_target_ml,
        "experience_level": profile.experience_level,
        "training_type": profile.training_type,
        "primary_goal": profile.primary_goal,
        "equipment": profile.equipment,
        "schedule": profile.schedule,
        "dietary_preferences": profile.dietary_preferences,
        "limitation_notes": profile.limitation_notes,
        "onboarding_step": profile.onboarding_step,
        "onboarding_completed": profile.onboarding_completed,
    }
    if db is not None:
        latest_weight = db.scalar(
            select(BodyMetricEntry)
            .where(
                BodyMetricEntry.athlete_id == profile.id,
                BodyMetricEntry.weight_kg.is_not(None),
            )
            .order_by(BodyMetricEntry.measured_at.desc())
        )
        payload["weight_kg"] = latest_weight.weight_kg if latest_weight else None
    return payload


@router.get("/onboarding")
def onboarding_state(
    profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)
):
    return {"profile": profile_payload(profile, db)}


@router.put("/onboarding")
def save_onboarding(
    payload: OnboardingPayload,
    profile: AthleteProfile = Depends(current_profile),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    data = payload.data
    if payload.step == 1:
        if "full_name" in data:
            user.full_name = str(data["full_name"]).strip()
        profile.height_cm = float(data["height_cm"])
        profile.unit_system = data.get("unit_system", "metric")
        profile.country = data.get("country", "India")
        profile.gender = data.get("gender")
        if data.get("date_of_birth"):
            profile.date_of_birth = date.fromisoformat(data["date_of_birth"])
        weight = float(data["weight_kg"])
        latest_weight = db.scalar(
            select(BodyMetricEntry)
            .where(
                BodyMetricEntry.athlete_id == profile.id,
                BodyMetricEntry.weight_kg.is_not(None),
            )
            .order_by(BodyMetricEntry.measured_at.desc())
        )
        if latest_weight is None or latest_weight.weight_kg != weight:
            db.add(
                BodyMetricEntry(athlete_id=profile.id, weight_kg=weight, source="onboarding")
            )
        user.timezone = data.get("timezone", user.timezone)
    elif payload.step == 2:
        profile.water_target_ml = int(data.get("water_target_ml", 3000))
        profile.sleep_hours = float(data.get("sleep_hours", 7))
        profile.activity_level = data.get("activity_level", "moderately_active")
    elif payload.step == 3:
        level = data.get("experience_level")
        if level not in {"beginner", "early_beginner", "intermediate", "advanced"}:
            raise DomainError("INVALID_EXPERIENCE_LEVEL", "Choose a supported experience level.")
        profile.experience_level = level
    elif payload.step == 4:
        training_type = data.get("training_type")
        if training_type not in {"bodybuilding", "calisthenics", "athletic", "aesthetic", "hybrid"}:
            raise DomainError("INVALID_TRAINING_TYPE", "Choose a supported training type.")
        profile.training_type = training_type
    elif payload.step == 5:
        profile.primary_goal = data.get("primary_goal")
    elif payload.step == 6:
        equipment = data.get("equipment", [])
        profile.equipment = equipment or ["bodyweight"]
    elif payload.step == 7:
        profile.schedule = {
            "days_per_week": int(data.get("days_per_week", 3)),
            "preferred_weekdays": data.get("preferred_weekdays", []),
            "session_minutes": int(data.get("session_minutes", 60)),
            "preferred_time": data.get("preferred_time", "evening"),
        }
    elif payload.step == 8:
        values = {key: data.get(key) for key in ("chest_cm", "waist_cm", "shoulders_cm", "arms_cm", "thighs_cm", "hips_cm", "neck_cm")}
        if any(value is not None for value in values.values()):
            db.add(BodyMetricEntry(athlete_id=profile.id, source="onboarding", **values))
    elif payload.step == 9:
        if data.get("cv_consent"):
            consent = db.scalar(
                select(Consent).where(Consent.user_id == user.id, Consent.consent_type == "cv_processing")
            )
            if not consent:
                consent = Consent(user_id=user.id, consent_type="cv_processing", version="1.0")
                db.add(consent)
            consent.granted_at = utcnow()
            consent.revoked_at = None
        profile.onboarding_completed = True
    profile.onboarding_step = 9 if profile.onboarding_completed else min(9, payload.step + 1)
    db.commit()
    if profile.onboarding_completed:
        generate_program(db, profile)
    return {"profile": profile_payload(profile, db)}


@router.get("/me/profile")
def get_profile(
    profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)
):
    return {"profile": profile_payload(profile, db)}


@router.post("/body-metrics", status_code=201)
def add_metric(
    payload: MetricPayload,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    if not any(value is not None for key, value in payload.model_dump().items() if key.endswith("_kg") or key.endswith("_cm")):
        raise DomainError("METRIC_REQUIRED", "Add at least one measurement.")
    entry = BodyMetricEntry(
        athlete_id=profile.id,
        measured_at=payload.measured_at or datetime.now(timezone.utc),
        **payload.model_dump(exclude={"measured_at"}),
    )
    db.add(entry)
    db.commit()
    return {"id": entry.id, "measured_at": entry.measured_at}


@router.get("/body-metrics")
def metric_history(
    profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(BodyMetricEntry)
        .where(BodyMetricEntry.athlete_id == profile.id)
        .order_by(BodyMetricEntry.measured_at.desc())
        .limit(365)
    ).all()
    return {
        "items": [
            {
                "id": row.id,
                "measured_at": row.measured_at,
                "weight_kg": row.weight_kg,
                "chest_cm": row.chest_cm,
                "waist_cm": row.waist_cm,
                "shoulders_cm": row.shoulders_cm,
                "arms_cm": row.arms_cm,
                "thighs_cm": row.thighs_cm,
                "hips_cm": row.hips_cm,
                "neck_cm": row.neck_cm,
                "source": row.source,
            }
            for row in rows
        ]
    }


@router.put("/readiness/{local_date}")
def put_readiness(
    local_date: date,
    payload: ReadinessPayload,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    values = payload.model_dump()
    score, explanation = calculate_readiness(values)
    row = db.scalar(
        select(ReadinessLog).where(
            ReadinessLog.athlete_id == profile.id, ReadinessLog.local_date == local_date
        )
    )
    if not row:
        row = ReadinessLog(athlete_id=profile.id, local_date=local_date, score=score)
        db.add(row)
    for key, value in values.items():
        setattr(row, key, value)
    row.score = score
    row.explanation = explanation
    db.commit()
    return {"score": score, "explanation": explanation, "disclaimer": "Readiness is fitness guidance, not medical advice."}

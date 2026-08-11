from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_profile, current_user
from app.errors import DomainError
from app.models import AthleteProfile, Consent, CvAssessment, RecommendationDecision, User

router = APIRouter(tags=["body-scan"])

ALLOWED_FEATURES = {
    "shoulder_to_hip_ratio",
    "torso_inclination_deg",
    "shoulder_line_angle_deg",
    "hip_line_angle_deg",
    "landmark_symmetry",
    "pose_rotation_proxy",
}


class AssessmentRequest(BaseModel):
    capture_type: str = Field(default="front", pattern="^(front|side)$")
    model_version: str = Field(min_length=2, max_length=64)
    feature_schema_version: str = Field(default="pose-ratios-v1", max_length=32)
    quality_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    quality_flags: list[str] = Field(default_factory=list, max_length=20)
    derived_features: dict[str, float | None] = Field(default_factory=dict)
    raw_media_stored: bool = False


def _assessment_payload(row: CvAssessment) -> dict:
    return {
        "id": row.id,
        "captured_at": row.captured_at,
        "capture_type": row.capture_type,
        "model_version": row.model_version,
        "feature_schema_version": row.feature_schema_version,
        "quality_score": row.quality_score,
        "confidence": row.confidence,
        "quality_flags": row.quality_flags,
        "derived_features": row.derived_features,
        "raw_media_stored": row.raw_media_stored,
        "disclaimer": "Visual analysis is approximate and is not a medical device or body-fat measurement.",
    }


@router.post("/cv/assessments", status_code=201)
def create_assessment(payload: AssessmentRequest, profile: AthleteProfile = Depends(current_profile), user: User = Depends(current_user), db: Session = Depends(get_db)):
    consent = db.scalar(select(Consent).where(Consent.user_id == user.id, Consent.consent_type == "cv_processing", Consent.granted_at.is_not(None), Consent.revoked_at.is_(None)))
    if not consent:
        raise DomainError("CV_CONSENT_REQUIRED", "Grant optional visual-analysis consent before saving derived scan data.", 403)
    if payload.raw_media_stored:
        raise DomainError("RAW_MEDIA_DISABLED", "Raw scan storage is disabled; only derived features are accepted.", 400)
    unexpected = set(payload.derived_features) - ALLOWED_FEATURES
    if unexpected:
        raise DomainError("UNKNOWN_CV_FEATURE", "The assessment contains an unsupported derived feature.", details={"features": sorted(unexpected)})
    derived = payload.derived_features if payload.quality_score >= 60 and payload.confidence >= 0.55 else {}
    row = CvAssessment(athlete_id=profile.id, **payload.model_dump(exclude={"derived_features"}), derived_features=derived)
    db.add(row)
    if derived:
        db.add(RecommendationDecision(athlete_id=profile.id, decision_type="cv_progress_context", evidence_snapshot={"assessment_id": row.id, "features": derived}, confidence=min(0.65, payload.confidence), explanation="This scan is stored for standardized progress comparison. Training changes still require performance and recovery evidence.", safety_checks=["cv_secondary_signal", "quality_gate_passed", "no_medical_inference"]))
    db.commit()
    return {"assessment": _assessment_payload(row)}


@router.get("/cv/assessments")
def list_assessments(profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    rows = db.scalars(select(CvAssessment).where(CvAssessment.athlete_id == profile.id).order_by(CvAssessment.captured_at.desc()).limit(50)).all()
    return {"items": [_assessment_payload(row) for row in rows]}


@router.delete("/cv/assessments/{assessment_id}", status_code=204)
def delete_assessment(assessment_id: str, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    row = db.scalar(select(CvAssessment).where(CvAssessment.id == assessment_id, CvAssessment.athlete_id == profile.id))
    if not row:
        raise DomainError("ASSESSMENT_NOT_FOUND", "Assessment was not found.", 404)
    db.delete(row)
    db.commit()


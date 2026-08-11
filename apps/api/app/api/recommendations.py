from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_profile
from app.errors import DomainError
from app.models import AthleteProfile, RecommendationDecision

router = APIRouter(tags=["recommendations"])


class OverrideRequest(BaseModel):
    status: str = Field(pattern="^(applied|rejected|user_overridden)$")
    reason: str | None = Field(default=None, max_length=500)


@router.get("/recommendations")
def list_recommendations(profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    rows = db.scalars(select(RecommendationDecision).where(RecommendationDecision.athlete_id == profile.id).order_by(RecommendationDecision.created_at.desc()).limit(50)).all()
    return {"items": [{"id": row.id, "decision_type": row.decision_type, "evidence": row.evidence_snapshot, "rule_set_version": row.rule_set_version, "confidence": row.confidence, "explanation": row.explanation, "safety_checks": row.safety_checks, "status": row.status, "effective_at": row.effective_at} for row in rows]}


@router.post("/recommendations/{recommendation_id}/override")
def override_recommendation(recommendation_id: str, payload: OverrideRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    row = db.scalar(select(RecommendationDecision).where(RecommendationDecision.id == recommendation_id, RecommendationDecision.athlete_id == profile.id))
    if not row:
        raise DomainError("RECOMMENDATION_NOT_FOUND", "Recommendation was not found.", 404)
    row.status = payload.status
    if payload.reason:
        row.evidence_snapshot = {**row.evidence_snapshot, "override_reason": payload.reason}
    db.commit()
    return {"id": row.id, "status": row.status}


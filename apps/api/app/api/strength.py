from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from statistics import fmean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_profile, current_user
from app.domains.strength import ANALYTICS_VERSION, build_strength_analysis
from app.errors import DomainError
from app.models import (
    AthleteProfile,
    ReadinessLog,
    SetLog,
    StrengthReport,
    User,
    WorkoutSession,
    new_id,
)
from app.strength_schemas import (
    MuscleDetailOut,
    StrengthAnalysisOut,
    StrengthPeriod,
    StrengthReportListOut,
    StrengthReportOut,
    StrengthReportRequest,
)

router = APIRouter(tags=["strength intelligence"])


def _analysis(
    db: Session,
    profile: AthleteProfile,
    user: User,
    period: StrengthPeriod,
    through: date | None,
) -> dict:
    return build_strength_analysis(
        db,
        athlete_id=profile.id,
        timezone_name=user.timezone,
        period=period,
        through=through,
    )


@router.get("/progress/strength", response_model=StrengthAnalysisOut)
def strength_progress(
    period: StrengthPeriod = Query(default="week"),
    through: date | None = Query(default=None),
    profile: AthleteProfile = Depends(current_profile),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return _analysis(db, profile, user, period, through)


@router.get(
    "/progress/strength/muscles/{muscle_id}", response_model=MuscleDetailOut
)
def muscle_strength_detail(
    muscle_id: str,
    period: StrengthPeriod = Query(default="week"),
    through: date | None = Query(default=None),
    profile: AthleteProfile = Depends(current_profile),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    analysis = _analysis(db, profile, user, period, through)
    muscle = next(
        (
            row
            for row in analysis["muscles"]
            if row["id"] == muscle_id or row["slug"] == muscle_id
        ),
        None,
    )
    if muscle is None:
        raise DomainError("MUSCLE_NOT_FOUND", "Muscle group was not found.", 404)
    return {
        "period": analysis["period"],
        "muscle": muscle,
        "trend": analysis["trend"],
        "recommendations": [
            row
            for row in analysis["recommendations"]
            if row["muscle"] in {None, muscle["name"]}
        ],
        "methodology_note": analysis["methodology_note"],
    }


def _timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _report_supporting_data(
    db: Session, profile: AthleteProfile, user: User, analysis: dict
) -> tuple[dict, dict]:
    period = analysis["period"]
    timezone_value = _timezone(user.timezone)
    start_dt = datetime.combine(period["start"], time.min, tzinfo=timezone_value).astimezone(
        timezone.utc
    )
    end_dt = datetime.combine(
        period["end"] + timedelta(days=1), time.min, tzinfo=timezone_value
    ).astimezone(timezone.utc)
    sessions = db.scalars(
        select(WorkoutSession).where(
            WorkoutSession.athlete_id == profile.id,
            WorkoutSession.started_at >= start_dt,
            WorkoutSession.started_at < end_dt,
        )
    ).all()
    completed = [session for session in sessions if session.status == "completed"]
    session_ids = [session.id for session in completed]
    sets = (
        db.scalars(
            select(SetLog).where(
                SetLog.workout_session_id.in_(session_ids), SetLog.completed.is_(True)
            )
        ).all()
        if session_ids
        else []
    )
    readiness = db.scalars(
        select(ReadinessLog).where(
            ReadinessLog.athlete_id == profile.id,
            ReadinessLog.local_date >= period["start"],
            ReadinessLog.local_date <= period["end"],
        )
    ).all()
    training = {
        "sessions": len(completed),
        "sessions_started": len(sessions),
        "working_sets": len(sets),
        "training_volume_kg": round(
            sum((row.load_kg or 0) * (row.reps or 0) for row in sets), 1
        ),
        "workout_completion_percent": (
            round(len(completed) / len(sessions) * 100, 1) if sessions else 0
        ),
    }
    sleep_values = [row.sleep_hours for row in readiness if row.sleep_hours is not None]
    recovery = {
        "average_sleep_hours": round(fmean(sleep_values), 1) if sleep_values else None,
        "average_readiness": (
            round(fmean(row.score for row in readiness), 1) if readiness else None
        ),
        "check_ins": len(readiness),
    }
    return training, recovery


def _summary(report: StrengthReport) -> dict:
    return {
        "id": report.id,
        "period_type": report.period_type,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "overall_score": report.overall_score,
        "generated_at": report.generated_at,
        "analytics_version": report.analytics_version,
    }


@router.post("/progress/strength-report", response_model=StrengthReportOut, status_code=201)
def generate_strength_report(
    payload: StrengthReportRequest,
    profile: AthleteProfile = Depends(current_profile),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    analysis = _analysis(db, profile, user, payload.period, payload.through)
    training, recovery = _report_supporting_data(db, profile, user, analysis)
    report_payload = jsonable_encoder(
        {
            "title": "ATHLETEOS STRENGTH REPORT",
            "analysis": analysis,
            "training_summary": training,
            "recovery": recovery,
            "recommendations": analysis["recommendations"],
            "generated_for": user.full_name,
        }
    )
    report = StrengthReport(
        id=new_id(),
        user_id=user.id,
        period_type=payload.period,
        period_start=analysis["period"]["start"],
        period_end=analysis["period"]["end"],
        overall_score=analysis["overall"]["score"],
        report_json=report_payload,
        analytics_version=ANALYTICS_VERSION,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {**_summary(report), "report": report.report_json}


@router.get("/progress/strength-reports", response_model=StrengthReportListOut)
def list_strength_reports(
    user: User = Depends(current_user), db: Session = Depends(get_db)
):
    reports = db.scalars(
        select(StrengthReport)
        .where(StrengthReport.user_id == user.id)
        .order_by(StrengthReport.generated_at.desc())
        .limit(24)
    ).all()
    return {"items": [_summary(report) for report in reports]}


@router.get("/progress/strength-reports/{report_id}", response_model=StrengthReportOut)
def get_strength_report(
    report_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    report = db.scalar(
        select(StrengthReport).where(
            StrengthReport.id == report_id, StrengthReport.user_id == user.id
        )
    )
    if report is None:
        raise DomainError("STRENGTH_REPORT_NOT_FOUND", "Strength report was not found.", 404)
    return {**_summary(report), "report": report.report_json}

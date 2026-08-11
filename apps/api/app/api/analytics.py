from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.nutrition import nutrition_day_payload
from app.db import get_db
from app.dependencies import current_profile, current_user
from app.domains.habits import calculate_streak, is_scheduled
from app.models import (
    AthleteProfile,
    BodyMetricEntry,
    Exercise,
    Habit,
    HabitCompletion,
    PersonalRecord,
    PrescribedExercise,
    Program,
    ProgramDay,
    ReadinessLog,
    RecommendationDecision,
    SetLog,
    User,
    WorkoutSession,
)

router = APIRouter(tags=["analytics"])


def _upcoming_day(db: Session, profile: AthleteProfile, local_date: date):
    return db.scalar(
        select(ProgramDay)
        .join(Program, ProgramDay.program_id == Program.id)
        .where(Program.athlete_id == profile.id, Program.status == "active", ProgramDay.scheduled_date >= local_date)
        .order_by(ProgramDay.scheduled_date, ProgramDay.day_index)
    ) or db.scalar(
        select(ProgramDay)
        .join(Program, ProgramDay.program_id == Program.id)
        .where(Program.athlete_id == profile.id, Program.status == "active")
        .order_by(ProgramDay.day_index)
    )


def _compact_day(db: Session, day: ProgramDay | None) -> dict | None:
    if not day:
        return None
    rows = db.execute(
        select(PrescribedExercise, Exercise)
        .join(Exercise, PrescribedExercise.exercise_id == Exercise.id)
        .where(PrescribedExercise.program_day_id == day.id)
        .order_by(PrescribedExercise.order_index)
    ).all()
    return {
        "id": day.id,
        "title": day.title,
        "focus": day.focus,
        "scheduled_date": day.scheduled_date,
        "estimated_minutes": day.estimated_minutes,
        "exercises": [
            {
                "name": exercise.name,
                "sets": prescription.target_sets,
                "rep_min": prescription.rep_min,
                "rep_max": prescription.rep_max,
                "target_seconds": prescription.target_seconds,
            }
            for prescription, exercise in rows
        ],
    }


@router.get("/dashboard/today")
def dashboard_today(
    local_date: date | None = Query(default=None),
    profile: AthleteProfile = Depends(current_profile),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    day = local_date or date.today()
    latest_metric = db.scalar(select(BodyMetricEntry).where(BodyMetricEntry.athlete_id == profile.id, BodyMetricEntry.weight_kg.is_not(None)).order_by(BodyMetricEntry.measured_at.desc()))
    habits = db.scalars(select(Habit).where(Habit.athlete_id == profile.id, Habit.active.is_(True)).order_by(Habit.created_at)).all()
    habit_items = []
    best_streak = 0
    for habit in habits:
        completions = db.scalars(select(HabitCompletion).where(HabitCompletion.habit_id == habit.id, HabitCompletion.local_date <= day)).all()
        completion = next((row for row in completions if row.local_date == day), None)
        streak = calculate_streak(habit, completions, day)
        best_streak = max(best_streak, streak["current"])
        habit_items.append({"id": habit.id, "name": habit.name, "derived": bool(habit.derived_source), "completed": bool(completion and completion.completed), "streak": streak["current"]})
    readiness = db.scalar(select(ReadinessLog).where(ReadinessLog.athlete_id == profile.id, ReadinessLog.local_date == day))
    prs = db.execute(
        select(PersonalRecord, Exercise)
        .join(Exercise, PersonalRecord.exercise_id == Exercise.id)
        .where(PersonalRecord.athlete_id == profile.id)
        .order_by(PersonalRecord.achieved_at.desc())
        .limit(3)
    ).all()
    recommendations = db.scalars(select(RecommendationDecision).where(RecommendationDecision.athlete_id == profile.id, RecommendationDecision.status == "proposed").order_by(RecommendationDecision.created_at.desc()).limit(3)).all()
    return {
        "user": {"first_name": user.full_name.split()[0], "full_name": user.full_name, "experience_level": profile.experience_level},
        "date": day,
        "metrics": {"weight_kg": latest_metric.weight_kg if latest_metric else None, "water_target_ml": profile.water_target_ml, "workout_streak": best_streak},
        "workout": _compact_day(db, _upcoming_day(db, profile, day)),
        "nutrition": nutrition_day_payload(db, profile, day),
        "habits": habit_items,
        "readiness": {"score": readiness.score, "explanation": readiness.explanation} if readiness else None,
        "recent_prs": [{"exercise": exercise.name, "type": pr.record_type, "value": pr.value, "achieved_at": pr.achieved_at} for pr, exercise in prs],
        "recommendations": [{"id": item.id, "type": item.decision_type, "explanation": item.explanation, "confidence": item.confidence} for item in recommendations],
    }


def _range_report(
    db: Session,
    profile: AthleteProfile,
    start: date,
    end: date,
    through: date | None = None,
) -> dict:
    report_through = min(end, through or date.today())
    has_elapsed_days = report_through >= start
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(
        (report_through + timedelta(days=1)) if has_elapsed_days else start,
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    sessions = db.scalars(select(WorkoutSession).where(WorkoutSession.athlete_id == profile.id, WorkoutSession.started_at >= start_dt, WorkoutSession.started_at < end_dt)).all()
    completed_sessions = [session for session in sessions if session.status == "completed"]
    session_ids = [session.id for session in completed_sessions]
    sets = db.scalars(select(SetLog).where(SetLog.workout_session_id.in_(session_ids))) .all() if session_ids else []
    metrics = db.scalars(select(BodyMetricEntry).where(BodyMetricEntry.athlete_id == profile.id, BodyMetricEntry.measured_at >= start_dt, BodyMetricEntry.measured_at < end_dt).order_by(BodyMetricEntry.measured_at)).all()
    habits = db.scalars(
        select(Habit).where(Habit.athlete_id == profile.id, Habit.active.is_(True))
    ).all()
    completions = (
        db.scalars(
            select(HabitCompletion).where(
                HabitCompletion.athlete_id == profile.id,
                HabitCompletion.local_date >= start,
                HabitCompletion.local_date <= report_through,
                HabitCompletion.completed.is_(True),
            )
        ).all()
        if has_elapsed_days
        else []
    )
    habits_by_id = {habit.id: habit for habit in habits}
    scheduled_completions = [
        completion
        for completion in completions
        if (habit := habits_by_id.get(completion.habit_id))
        and is_scheduled(habit, completion.local_date)
    ]
    expected = 0
    if has_elapsed_days:
        for offset in range((report_through - start).days + 1):
            local_day = start + timedelta(days=offset)
            expected += sum(1 for habit in habits if is_scheduled(habit, local_day))
    return {
        "period": {"from": start, "to": end},
        "training": {"sessions_started": len(sessions), "sessions_completed": len(completed_sessions), "sets_completed": sum(1 for row in sets if row.completed), "volume_kg": round(sum((row.load_kg or 0) * (row.reps or 0) for row in sets if row.completed), 1)},
        "body": {"weight_series": [{"date": row.measured_at.date(), "value": row.weight_kg} for row in metrics if row.weight_kg is not None], "weight_change_kg": round((next((row.weight_kg for row in reversed(metrics) if row.weight_kg is not None), 0) or 0) - (next((row.weight_kg for row in metrics if row.weight_kg is not None), 0) or 0), 2) if metrics else None},
        "habits": {
            "completions": len(scheduled_completions),
            "completion_rate": (
                round(len(scheduled_completions) / expected * 100, 1) if expected else 0
            ),
        },
        "data_note": "Missing dates remain missing; they are not treated as zero measurements.",
    }


@router.get("/reports/weekly")
def weekly_report(
    week_of: date | None = Query(default=None),
    through: date | None = Query(default=None),
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    anchor = week_of or through or date.today()
    start = anchor - timedelta(days=anchor.weekday())
    return _range_report(db, profile, start, start + timedelta(days=6), through)


@router.get("/reports/monthly")
def monthly_report(
    month: str | None = None,
    through: date | None = Query(default=None),
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    if month:
        year, month_number = [int(part) for part in month.split("-", 1)]
        start = date(year, month_number, 1)
    else:
        today = through or date.today()
        start = today.replace(day=1)
    next_month = date(start.year + (1 if start.month == 12 else 0), 1 if start.month == 12 else start.month + 1, 1)
    return _range_report(db, profile, start, next_month - timedelta(days=1), through)

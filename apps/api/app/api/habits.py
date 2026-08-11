from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_profile
from app.domains.habits import calculate_streak, is_scheduled, month_dates
from app.errors import DomainError
from app.models import AthleteProfile, Habit, HabitCompletion

router = APIRouter(tags=["habits"])


class HabitRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    category: str = Field(default="wellness", max_length=32)
    measurement_type: str = Field(default="boolean", pattern="^(boolean|count|minutes|ml)$")
    target_value: float = Field(default=1, gt=0)
    target_unit: str | None = Field(default=None, max_length=24)
    schedule: dict = Field(default_factory=lambda: {"frequency": "daily"})


class CompletionRequest(BaseModel):
    value: float = Field(default=1, ge=0)
    completed: bool = True


def _owned_habit(db: Session, athlete_id: str, habit_id: str) -> Habit:
    habit = db.scalar(select(Habit).where(Habit.id == habit_id, Habit.athlete_id == athlete_id))
    if not habit:
        raise DomainError("HABIT_NOT_FOUND", "Habit was not found.", 404)
    return habit


def _habit_payload(db: Session, habit: Habit, through: date) -> dict:
    completions = db.scalars(select(HabitCompletion).where(HabitCompletion.habit_id == habit.id, HabitCompletion.local_date <= through)).all()
    return {
        "id": habit.id,
        "name": habit.name,
        "category": habit.category,
        "measurement_type": habit.measurement_type,
        "target_value": habit.target_value,
        "target_unit": habit.target_unit,
        "schedule": habit.schedule,
        "active": habit.active,
        "derived_source": habit.derived_source,
        "streak": calculate_streak(habit, completions, through),
    }


@router.get("/habits")
def list_habits(profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    rows = db.scalars(select(Habit).where(Habit.athlete_id == profile.id, Habit.active.is_(True)).order_by(Habit.created_at)).all()
    return {"items": [_habit_payload(db, row, date.today()) for row in rows]}


@router.post("/habits", status_code=201)
def create_habit(payload: HabitRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    habit = Habit(athlete_id=profile.id, **payload.model_dump())
    db.add(habit)
    db.commit()
    return {"habit": _habit_payload(db, habit, date.today())}


@router.put("/habits/{habit_id}")
def update_habit(habit_id: str, payload: HabitRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    habit = _owned_habit(db, profile.id, habit_id)
    for key, value in payload.model_dump().items():
        setattr(habit, key, value)
    db.commit()
    return {"habit": _habit_payload(db, habit, date.today())}


@router.put("/habits/{habit_id}/days/{local_date}")
def set_completion(habit_id: str, local_date: date, payload: CompletionRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    habit = _owned_habit(db, profile.id, habit_id)
    if habit.derived_source:
        raise DomainError("DERIVED_HABIT_READ_ONLY", "This habit updates from its source activity.", 409)
    row = db.scalar(select(HabitCompletion).where(HabitCompletion.habit_id == habit.id, HabitCompletion.athlete_id == profile.id, HabitCompletion.local_date == local_date))
    if not row:
        row = HabitCompletion(habit_id=habit.id, athlete_id=profile.id, local_date=local_date)
        db.add(row)
    row.value = payload.value
    row.completed = payload.completed
    db.commit()
    return {"completion": {"habit_id": habit.id, "local_date": local_date, "value": row.value, "completed": row.completed}, "streak": _habit_payload(db, habit, date.today())["streak"]}


@router.get("/habit-grid")
def habit_grid(month: str, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    try:
        dates = month_dates(month)
    except (ValueError, TypeError):
        raise DomainError("INVALID_MONTH", "Month must use YYYY-MM format.") from None
    habits = db.scalars(select(Habit).where(Habit.athlete_id == profile.id, Habit.active.is_(True)).order_by(Habit.created_at)).all()
    start, end = dates[0], dates[-1]
    rows = []
    for habit in habits:
        completions = db.scalars(select(HabitCompletion).where(HabitCompletion.habit_id == habit.id, HabitCompletion.local_date >= start, HabitCompletion.local_date <= end)).all()
        values = {item.local_date.isoformat(): {"value": item.value, "completed": item.completed} for item in completions}
        rows.append({**_habit_payload(db, habit, date.today()), "days": values, "scheduled_days": [day.isoformat() for day in dates if is_scheduled(habit, day)]})
    return {"month": month, "dates": [day.isoformat() for day in dates], "rows": rows}


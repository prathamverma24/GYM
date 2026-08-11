from collections import Counter, defaultdict
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import current_profile
from app.domains.catalog import normalize_text
from app.domains.program_editing import (
    activate_template,
    add_day,
    add_exercise,
    owned_active_program,
    remove_day,
    remove_exercise,
    update_day,
    update_exercise,
)
from app.domains.training import generate_program
from app.errors import DomainError
from app.models import (
    AthleteProfile,
    Exercise,
    ExerciseSubstitutionGroup,
    Habit,
    HabitCompletion,
    PersonalRecord,
    PrescribedExercise,
    Program,
    ProgramDay,
    ProgressionRuleDefinition,
    RecommendationDecision,
    ResearchSource,
    SetLog,
    WorkoutDayTemplate,
    WorkoutPrescriptionTemplate,
    WorkoutSession,
    WorkoutSplitTemplate,
)

router = APIRouter(tags=["training"])


class StartWorkoutRequest(BaseModel):
    program_day_id: str


class SetRequest(BaseModel):
    prescribed_exercise_id: str
    set_index: int = Field(ge=1, le=20)
    client_operation_id: str = Field(min_length=8, max_length=64)
    load_kg: float | None = Field(default=None, ge=0, le=1000)
    reps: int | None = Field(default=None, ge=0, le=1000)
    seconds: int | None = Field(default=None, ge=0, le=86400)
    distance_m: float | None = Field(default=None, ge=0, le=1_000_000)
    assistance_kg: float | None = Field(default=None, ge=0, le=1000)
    rir: int | None = Field(default=None, ge=0, le=10)
    rpe: float | None = Field(default=None, ge=1, le=10)
    completed: bool = True
    notes: str | None = Field(default=None, max_length=1000)


class SetUpdateRequest(BaseModel):
    load_kg: float | None = Field(default=None, ge=0, le=1000)
    reps: int | None = Field(default=None, ge=0, le=1000)
    seconds: int | None = Field(default=None, ge=0, le=86400)
    distance_m: float | None = Field(default=None, ge=0, le=1_000_000)
    assistance_kg: float | None = Field(default=None, ge=0, le=1000)
    rir: int | None = Field(default=None, ge=0, le=10)
    rpe: float | None = Field(default=None, ge=1, le=10)
    completed: bool = True
    notes: str | None = Field(default=None, max_length=1000)


class CompleteWorkoutRequest(BaseModel):
    session_rpe: int | None = Field(default=None, ge=1, le=10)
    rating: str | None = Field(default=None, pattern="^(easy|good|hard|too_hard)$")
    notes: str | None = Field(default=None, max_length=2000)


class ProgramDayRequest(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    focus: list[str] = Field(default_factory=list, max_length=8)
    scheduled_date: date | None = None
    estimated_minutes: int = Field(default=60, ge=15, le=240)


class PlannedExerciseRequest(BaseModel):
    exercise_id: str
    order_index: int | None = Field(default=None, ge=1, le=30)
    target_sets: int | None = Field(default=None, ge=1, le=10)
    rep_min: int | None = Field(default=None, ge=1, le=1000)
    rep_max: int | None = Field(default=None, ge=1, le=1000)
    target_seconds: int | None = Field(default=None, ge=1, le=86400)
    rest_seconds: int | None = Field(default=None, ge=0, le=1800)
    target_rir: int | None = Field(default=None, ge=0, le=10)
    notes: str | None = Field(default=None, max_length=1000)


def _exercise_payload(exercise: Exercise) -> dict:
    return {
        "id": exercise.id,
        "source_id": exercise.source_id,
        "name": exercise.name,
        "slug": exercise.slug,
        "category": exercise.category,
        "primary_muscles": exercise.primary_muscles,
        "secondary_muscles": exercise.secondary_muscles,
        "movement_pattern": exercise.movement_pattern,
        "equipment": exercise.equipment,
        "equipment_display": exercise.equipment_display,
        "equipment_options": exercise.equipment_options,
        "difficulty": exercise.difficulty,
        "training_types": exercise.training_types,
        "is_compound": exercise.is_compound,
        "is_unilateral": exercise.is_unilateral,
        "tracking_metric": exercise.tracking_metric,
        "minimum_level": exercise.minimum_level,
        "modality": exercise.modality,
        "instructions": exercise.instructions,
        "safety_notes": exercise.safety_notes,
        "default_sets": exercise.default_sets,
        "default_rep_min": exercise.default_rep_min,
        "default_rep_max": exercise.default_rep_max,
        "default_seconds": exercise.default_seconds,
        "rest_seconds": exercise.rest_seconds,
        "source_version": exercise.source_version,
        "version": exercise.version,
    }


def _day_payload(db: Session, day: ProgramDay, athlete_id: str) -> dict:
    prescriptions = db.scalars(
        select(PrescribedExercise)
        .where(PrescribedExercise.program_day_id == day.id)
        .order_by(PrescribedExercise.order_index)
    ).all()
    items = []
    for prescription in prescriptions:
        exercise = db.get(Exercise, prescription.exercise_id)
        previous = db.execute(
            select(SetLog.load_kg, SetLog.reps, SetLog.rir)
            .join(WorkoutSession, SetLog.workout_session_id == WorkoutSession.id)
            .join(PrescribedExercise, SetLog.prescribed_exercise_id == PrescribedExercise.id)
            .where(
                WorkoutSession.athlete_id == athlete_id,
                WorkoutSession.status == "completed",
                PrescribedExercise.exercise_id == exercise.id,
                SetLog.completed.is_(True),
            )
            .order_by(WorkoutSession.completed_at.desc(), SetLog.set_index)
            .limit(prescription.target_sets)
        ).all()
        items.append(
            {
                "id": prescription.id,
                "order_index": prescription.order_index,
                "target_sets": prescription.target_sets,
                "rep_min": prescription.rep_min,
                "rep_max": prescription.rep_max,
                "target_seconds": prescription.target_seconds,
                "rest_seconds": prescription.rest_seconds,
                "target_rir": prescription.target_rir,
                "notes": prescription.notes,
                "exercise": _exercise_payload(exercise),
                "previous": [
                    {"load_kg": row.load_kg, "reps": row.reps, "rir": row.rir} for row in previous
                ],
            }
        )
    return {
        "id": day.id,
        "program_id": day.program_id,
        "day_index": day.day_index,
        "title": day.title,
        "focus": day.focus,
        "scheduled_date": day.scheduled_date,
        "estimated_minutes": day.estimated_minutes,
        "exercises": items,
    }


def _owned_day(db: Session, athlete_id: str, day_id: str) -> ProgramDay:
    day = db.scalar(
        select(ProgramDay)
        .join(Program, ProgramDay.program_id == Program.id)
        .where(ProgramDay.id == day_id, Program.athlete_id == athlete_id)
    )
    if not day:
        raise DomainError("PROGRAM_DAY_NOT_FOUND", "Training day was not found.", 404)
    return day


def _owned_session(db: Session, athlete_id: str, session_id: str) -> WorkoutSession:
    session = db.scalar(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id, WorkoutSession.athlete_id == athlete_id
        )
    )
    if not session:
        raise DomainError("WORKOUT_NOT_FOUND", "Workout session was not found.", 404)
    return session


@router.get("/exercises")
def exercises(
    q: str = "",
    equipment: str | None = None,
    training_type: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
    movement_pattern: str | None = None,
    muscle: str | None = None,
    tracking_metric: str | None = None,
    compound: bool | None = None,
    unilateral: bool | None = None,
    page: int = 1,
    page_size: int = 24,
    db: Session = Depends(get_db),
):
    page = max(1, page)
    page_size = max(1, min(60, page_size))
    all_rows = db.scalars(
        select(Exercise)
        .where(Exercise.published.is_(True), Exercise.source_id.is_not(None))
        .order_by(Exercise.category, Exercise.name)
    ).all()
    rows = list(all_rows)
    if q:
        needle = normalize_text(q)
        rows = [
            row
            for row in rows
            if needle
            in normalize_text(
                " ".join(
                    [
                        row.name,
                        row.category,
                        row.movement_pattern,
                        *row.primary_muscles,
                        *row.secondary_muscles,
                        row.equipment_display or "",
                    ]
                )
            )
        ]
    if equipment:
        rows = [row for row in rows if equipment in row.equipment]
    if training_type:
        rows = [row for row in rows if training_type in row.training_types]
    if category:
        rows = [row for row in rows if row.category == category]
    if difficulty:
        rows = [row for row in rows if row.difficulty == difficulty]
    if movement_pattern:
        rows = [row for row in rows if row.movement_pattern == movement_pattern]
    if muscle:
        rows = [
            row
            for row in rows
            if muscle in row.primary_muscles or muscle in row.secondary_muscles
        ]
    if tracking_metric:
        rows = [row for row in rows if row.tracking_metric == tracking_metric]
    if compound is not None:
        rows = [row for row in rows if row.is_compound is compound]
    if unilateral is not None:
        rows = [row for row in rows if row.is_unilateral is unilateral]
    total = len(rows)
    start = (page - 1) * page_size

    def facet(values: list[str]) -> list[dict]:
        return [
            {"value": value, "count": count}
            for value, count in sorted(Counter(values).items(), key=lambda item: item[0].lower())
        ]

    return {
        "items": [_exercise_payload(row) for row in rows[start : start + page_size]],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
        "facets": {
            "categories": facet([row.category for row in all_rows]),
            "equipment": facet([item for row in all_rows for item in row.equipment]),
            "difficulties": facet([row.difficulty for row in all_rows]),
            "training_types": facet([item for row in all_rows for item in row.training_types]),
            "tracking_metrics": facet([row.tracking_metric for row in all_rows]),
            "movement_patterns": facet([row.movement_pattern for row in all_rows]),
            "muscles": facet(
                [item for row in all_rows for item in [*row.primary_muscles, *row.secondary_muscles]]
            ),
        },
        "dataset": {
            "version": "1.0",
            "exercise_count": len(all_rows),
            "split_template_count": db.scalar(
                select(func.count()).select_from(WorkoutSplitTemplate)
            ),
            "prescription_count": db.scalar(
                select(func.count()).select_from(WorkoutPrescriptionTemplate)
            ),
        },
    }


@router.get("/exercise-module")
def exercise_module_overview(db: Session = Depends(get_db)):
    splits = db.scalars(
        select(WorkoutSplitTemplate).order_by(
            WorkoutSplitTemplate.days_per_week, WorkoutSplitTemplate.name
        )
    ).all()
    sources = db.scalars(select(ResearchSource).order_by(ResearchSource.source_id)).all()
    return {
        "counts": {
            "exercises": db.scalar(
                select(func.count()).select_from(Exercise).where(Exercise.source_id.is_not(None))
            ),
            "splits": len(splits),
            "day_templates": db.scalar(select(func.count()).select_from(WorkoutDayTemplate)),
            "prescriptions": db.scalar(
                select(func.count()).select_from(WorkoutPrescriptionTemplate)
            ),
            "progression_rules": db.scalar(
                select(func.count()).select_from(ProgressionRuleDefinition)
            ),
            "substitution_groups": db.scalar(
                select(func.count()).select_from(ExerciseSubstitutionGroup)
            ),
        },
        "splits": [
            {
                "id": split.source_id,
                "name": split.name,
                "days_per_week": split.days_per_week,
                "approach_family": split.approach_family,
                "athlete_types": split.athlete_types,
                "primary_goals": split.primary_goals,
                "description": split.description,
            }
            for split in splits
        ],
        "research_sources": [
            {
                "id": source.source_id,
                "topic": source.topic,
                "evidence_summary": source.evidence_summary,
                "url": source.url,
                "accessed": source.accessed,
            }
            for source in sources
        ],
    }


@router.get("/exercises/{exercise_id}")
def exercise_detail(exercise_id: str, db: Session = Depends(get_db)):
    exercise = db.get(Exercise, exercise_id)
    if not exercise or not exercise.published:
        raise DomainError("EXERCISE_NOT_FOUND", "Exercise was not found.", 404)
    usage_rows = []
    if exercise.source_id:
        usage_rows = db.execute(
            select(
                WorkoutPrescriptionTemplate,
                WorkoutDayTemplate,
                WorkoutSplitTemplate,
                ProgressionRuleDefinition,
            )
            .join(
                WorkoutDayTemplate,
                WorkoutPrescriptionTemplate.day_template_source_id
                == WorkoutDayTemplate.source_id,
            )
            .join(
                WorkoutSplitTemplate,
                WorkoutDayTemplate.split_source_id == WorkoutSplitTemplate.source_id,
            )
            .join(
                ProgressionRuleDefinition,
                WorkoutPrescriptionTemplate.progression_rule_source_id
                == ProgressionRuleDefinition.source_id,
            )
            .where(WorkoutPrescriptionTemplate.exercise_source_id == exercise.source_id)
            .order_by(
                WorkoutSplitTemplate.days_per_week,
                WorkoutSplitTemplate.name,
                WorkoutDayTemplate.day_order,
            )
        ).all()
    groups = db.scalars(select(ExerciseSubstitutionGroup)).all()
    substitutions = [
        group
        for group in groups
        if exercise.name == group.default_exercise or exercise.name in group.alternatives
    ]
    name_map = {
        item.name: item
        for item in db.scalars(
            select(Exercise).where(Exercise.published.is_(True), Exercise.source_id.is_not(None))
        ).all()
    }
    progression_rules = {}
    for _, _, _, rule in usage_rows:
        progression_rules[rule.source_id] = rule
    return {
        "exercise": _exercise_payload(exercise),
        "template_usage": {
            "total": len(usage_rows),
            "items": [
                {
                    "prescription_id": prescription.source_id,
                    "split_id": split.source_id,
                    "split_name": split.name,
                    "days_per_week": split.days_per_week,
                    "day_name": day.name,
                    "day_focus": day.focus,
                    "sets": prescription.sets,
                    "rep_min": prescription.rep_min,
                    "rep_max": prescription.rep_max,
                    "target_rir": prescription.target_rir,
                    "rest_seconds": prescription.rest_seconds,
                    "optional": prescription.is_optional,
                    "progression_rule_id": rule.source_id,
                }
                for prescription, day, split, rule in usage_rows[:24]
            ],
        },
        "substitutions": [
            {
                "group_id": group.source_id,
                "name": group.name,
                "logic": group.logic,
                "exercises": [
                    {
                        "id": candidate.id,
                        "name": candidate.name,
                        "equipment_display": candidate.equipment_display,
                        "difficulty": candidate.difficulty,
                    }
                    for candidate_name in [group.default_exercise, *group.alternatives]
                    if (candidate := name_map.get(candidate_name)) is not None
                ],
            }
            for group in substitutions
        ],
        "progression_rules": [
            {
                "id": rule.source_id,
                "name": rule.name,
                "applies_to": rule.applies_to,
                "trigger": rule.trigger,
                "action": rule.action,
                "regression": rule.regression,
                "notes": rule.notes,
            }
            for rule in progression_rules.values()
        ],
    }


def _active_program(db: Session, athlete_id: str) -> Program | None:
    return db.scalar(
        select(Program)
        .where(Program.athlete_id == athlete_id, Program.status == "active")
        .order_by(Program.created_at.desc())
    )


def _program_payload(db: Session, program: Program, athlete_id: str) -> dict:
    days = db.scalars(
        select(ProgramDay)
        .where(ProgramDay.program_id == program.id)
        .order_by(ProgramDay.day_index)
    ).all()
    return {
        "id": program.id,
        "name": program.name,
        "generator_version": program.generator_version,
        "rationale": program.rationale,
        "starts_on": program.starts_on,
        "days": [_day_payload(db, day, athlete_id) for day in days],
    }


def _editable_day(db: Session, program: Program, day_id: str) -> ProgramDay:
    day = db.scalar(
        select(ProgramDay).where(ProgramDay.id == day_id, ProgramDay.program_id == program.id)
    )
    if not day:
        raise DomainError("PROGRAM_DAY_NOT_FOUND", "Training day was not found.", 404)
    return day


def _published_exercise(db: Session, exercise_id: str) -> Exercise:
    exercise = db.scalar(
        select(Exercise).where(Exercise.id == exercise_id, Exercise.published.is_(True))
    )
    if not exercise:
        raise DomainError("EXERCISE_NOT_FOUND", "Exercise was not found.", 404)
    return exercise


def _validate_rep_range(payload: PlannedExerciseRequest) -> None:
    if payload.rep_min is not None and payload.rep_max is not None and payload.rep_min > payload.rep_max:
        raise DomainError("INVALID_REP_RANGE", "Minimum reps cannot be greater than maximum reps.")


@router.get("/programs/templates")
def program_templates(
    profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)
):
    requested_days = int(profile.schedule.get("days_per_week", 3))
    experience = (profile.experience_level or "beginner").replace("_", " ").casefold()
    athlete_type = (profile.training_type or "general").replace("_", " ").casefold()
    goal = (profile.primary_goal or "general fitness").replace("_", " ").casefold()
    ranks = {"beginner": 0, "early beginner": 1, "intermediate": 2, "advanced": 3}
    templates = db.scalars(
        select(WorkoutSplitTemplate).order_by(
            WorkoutSplitTemplate.days_per_week, WorkoutSplitTemplate.name
        )
    ).all()
    items = []
    for template in templates:
        min_rank = ranks.get(template.experience_min.casefold(), 0)
        max_rank = ranks.get(template.experience_max.casefold(), 3)
        level_match = min_rank <= ranks.get(experience, 0) <= max_rank
        type_match = any(athlete_type in value.casefold() for value in template.athlete_types)
        goal_match = any(
            goal in value.casefold() or value.casefold() in goal for value in template.primary_goals
        )
        items.append(
            {
                "id": template.source_id,
                "name": template.name,
                "approach_family": template.approach_family,
                "days_per_week": template.days_per_week,
                "experience_min": template.experience_min,
                "experience_max": template.experience_max,
                "primary_goals": template.primary_goals,
                "athlete_types": template.athlete_types,
                "session_minutes": template.session_minutes,
                "equipment_requirement": template.equipment_requirement,
                "recovery_demand": template.recovery_demand,
                "description": template.description,
                "recommended": template.days_per_week == requested_days
                and level_match
                and (type_match or goal_match),
            }
        )
    return {"items": items, "total": len(items)}


@router.post("/programs/templates/{split_id}/activate", status_code=201)
def activate_program_template(
    split_id: str,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    program = activate_template(db, profile, split_id)
    return {"program": _program_payload(db, program, profile.id)}


@router.post("/programs/generate", status_code=201)
def create_program(profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    program = generate_program(db, profile)
    return {"program_id": program.id, "name": program.name, "rationale": program.rationale}


@router.get("/programs/active")
def active_program(profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    program = _active_program(db, profile.id)
    if not program:
        return {"program": None}
    return {"program": _program_payload(db, program, profile.id)}


@router.post("/programs/{program_id}/days", status_code=201)
def create_program_day(
    program_id: str,
    payload: ProgramDayRequest,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    program = owned_active_program(db, profile.id, program_id)
    new_program, day = add_day(
        db,
        program,
        title=payload.title.strip(),
        focus=[value.strip() for value in payload.focus if value.strip()],
        scheduled_date=payload.scheduled_date,
        estimated_minutes=payload.estimated_minutes,
    )
    return {"program_id": new_program.id, "day_id": day.id}


@router.patch("/programs/{program_id}/days/{day_id}")
def edit_program_day(
    program_id: str,
    day_id: str,
    payload: ProgramDayRequest,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    program = owned_active_program(db, profile.id, program_id)
    current_day = _editable_day(db, program, day_id)
    new_program, day = update_day(
        db,
        program,
        day_id,
        title=payload.title.strip(),
        focus=[value.strip() for value in payload.focus if value.strip()],
        scheduled_date=(
            payload.scheduled_date
            if "scheduled_date" in payload.model_fields_set
            else current_day.scheduled_date
        ),
        estimated_minutes=payload.estimated_minutes,
    )
    return {"program_id": new_program.id, "day_id": day.id}


@router.delete("/programs/{program_id}/days/{day_id}", status_code=204)
def delete_program_day(
    program_id: str,
    day_id: str,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    program = owned_active_program(db, profile.id, program_id)
    _editable_day(db, program, day_id)
    remove_day(db, program, day_id)


@router.post("/programs/{program_id}/days/{day_id}/exercises", status_code=201)
def create_planned_exercise(
    program_id: str,
    day_id: str,
    payload: PlannedExerciseRequest,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    _validate_rep_range(payload)
    program = owned_active_program(db, profile.id, program_id)
    _editable_day(db, program, day_id)
    exercise = _published_exercise(db, payload.exercise_id)
    new_program, day, item = add_exercise(
        db, program, day_id, exercise, payload.model_dump(exclude={"exercise_id", "order_index"})
    )
    return {"program_id": new_program.id, "day_id": day.id, "prescribed_exercise_id": item.id}


@router.patch("/programs/{program_id}/days/{day_id}/exercises/{prescribed_exercise_id}")
def edit_planned_exercise(
    program_id: str,
    day_id: str,
    prescribed_exercise_id: str,
    payload: PlannedExerciseRequest,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    _validate_rep_range(payload)
    program = owned_active_program(db, profile.id, program_id)
    _editable_day(db, program, day_id)
    exercise = _published_exercise(db, payload.exercise_id)
    new_program, day, item = update_exercise(
        db,
        program,
        day_id,
        prescribed_exercise_id,
        exercise,
        payload.model_dump(exclude={"exercise_id"}),
    )
    return {"program_id": new_program.id, "day_id": day.id, "prescribed_exercise_id": item.id}


@router.delete("/programs/{program_id}/days/{day_id}/exercises/{prescribed_exercise_id}")
def delete_planned_exercise(
    program_id: str,
    day_id: str,
    prescribed_exercise_id: str,
    profile: AthleteProfile = Depends(current_profile),
    db: Session = Depends(get_db),
):
    program = owned_active_program(db, profile.id, program_id)
    _editable_day(db, program, day_id)
    new_program, day = remove_exercise(db, program, day_id, prescribed_exercise_id)
    return {"program_id": new_program.id, "day_id": day.id}


@router.get("/training/days/{day_id}")
def training_day(day_id: str, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    return {"day": _day_payload(db, _owned_day(db, profile.id, day_id), profile.id)}


@router.post("/workouts", status_code=201)
def start_workout(payload: StartWorkoutRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    _owned_day(db, profile.id, payload.program_day_id)
    existing = db.scalar(
        select(WorkoutSession).where(
            WorkoutSession.athlete_id == profile.id,
            WorkoutSession.program_day_id == payload.program_day_id,
            WorkoutSession.status == "active",
        )
    )
    if existing:
        return {"session_id": existing.id, "resumed": True}
    session = WorkoutSession(athlete_id=profile.id, program_day_id=payload.program_day_id)
    db.add(session)
    db.commit()
    return {"session_id": session.id, "resumed": False}


def _session_payload(db: Session, session: WorkoutSession) -> dict:
    day = db.get(ProgramDay, session.program_day_id)
    logs = db.scalars(
        select(SetLog).where(SetLog.workout_session_id == session.id).order_by(SetLog.created_at)
    ).all()
    return {
        "id": session.id,
        "status": session.status,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "session_rpe": session.session_rpe,
        "rating": session.rating,
        "notes": session.notes,
        "total_volume_kg": session.total_volume_kg,
        "day": _day_payload(db, day, session.athlete_id),
        "sets": [
            {
                "id": item.id,
                "prescribed_exercise_id": item.prescribed_exercise_id,
                "set_index": item.set_index,
                "client_operation_id": item.client_operation_id,
                "load_kg": item.load_kg,
                "reps": item.reps,
                "seconds": item.seconds,
                "distance_m": item.distance_m,
                "assistance_kg": item.assistance_kg,
                "rir": item.rir,
                "rpe": item.rpe,
                "completed": item.completed,
                "notes": item.notes,
            }
            for item in logs
        ],
    }


@router.get("/workouts/{session_id}")
def get_workout(session_id: str, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    return {"session": _session_payload(db, _owned_session(db, profile.id, session_id))}


@router.post("/workouts/{session_id}/sets", status_code=201)
def log_set(session_id: str, payload: SetRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    session = _owned_session(db, profile.id, session_id)
    if session.status != "active":
        raise DomainError("WORKOUT_ALREADY_COMPLETED", "Completed workouts cannot receive new sets.", 409)
    existing = db.scalar(select(SetLog).where(SetLog.client_operation_id == payload.client_operation_id))
    if existing:
        if existing.workout_session_id != session.id:
            raise DomainError("IDEMPOTENCY_CONFLICT", "This operation ID belongs to another workout.", 409)
        return {"set": {"id": existing.id, **payload.model_dump()}, "idempotent_replay": True}
    prescription = db.scalar(
        select(PrescribedExercise).where(
            PrescribedExercise.id == payload.prescribed_exercise_id,
            PrescribedExercise.program_day_id == session.program_day_id,
        )
    )
    if not prescription:
        raise DomainError("PRESCRIPTION_NOT_FOUND", "Exercise prescription is not part of this workout.", 404)
    exercise = db.get(Exercise, prescription.exercise_id)
    if exercise.modality in {"weighted_reps", "bodyweight_reps", "assisted_reps"} and payload.reps is None:
        raise DomainError("REPS_REQUIRED", "Reps are required for this exercise.")
    if exercise.modality == "isometric_hold" and payload.seconds is None:
        raise DomainError("SECONDS_REQUIRED", "Hold time is required for this exercise.")
    row = SetLog(workout_session_id=session.id, **payload.model_dump())
    db.add(row)
    db.commit()
    return {"set": {"id": row.id, **payload.model_dump()}, "idempotent_replay": False}


@router.patch("/workouts/{session_id}/sets/{set_id}")
def update_set(session_id: str, set_id: str, payload: SetUpdateRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    session = _owned_session(db, profile.id, session_id)
    if session.status != "active":
        raise DomainError("WORKOUT_ALREADY_COMPLETED", "Completed workouts cannot be edited.", 409)
    row = db.scalar(select(SetLog).where(SetLog.id == set_id, SetLog.workout_session_id == session.id))
    if not row:
        raise DomainError("SET_NOT_FOUND", "Set was not found.", 404)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return {"set_id": row.id}


@router.delete("/workouts/{session_id}/sets/{set_id}", status_code=204)
def delete_set(session_id: str, set_id: str, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    session = _owned_session(db, profile.id, session_id)
    if session.status != "active":
        raise DomainError("WORKOUT_ALREADY_COMPLETED", "Completed workouts cannot be edited.", 409)
    row = db.scalar(select(SetLog).where(SetLog.id == set_id, SetLog.workout_session_id == session.id))
    if not row:
        raise DomainError("SET_NOT_FOUND", "Set was not found.", 404)
    db.delete(row)
    db.commit()


@router.post("/workouts/{session_id}/complete")
def complete_workout(session_id: str, payload: CompleteWorkoutRequest, profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    session = _owned_session(db, profile.id, session_id)
    if session.status == "completed":
        return {"summary": _session_payload(db, session), "idempotent_replay": True}
    logs = db.scalars(select(SetLog).where(SetLog.workout_session_id == session.id, SetLog.completed.is_(True))).all()
    if not logs:
        raise DomainError("NO_COMPLETED_SETS", "Complete at least one set before finishing the workout.")
    session.status = "completed"
    session.completed_at = datetime.now(timezone.utc)
    session.session_rpe = payload.session_rpe
    session.rating = payload.rating
    session.notes = payload.notes
    session.total_volume_kg = round(sum((row.load_kg or 0) * (row.reps or 0) for row in logs), 2)
    workout_habit = db.scalar(
        select(Habit).where(
            Habit.athlete_id == profile.id,
            Habit.derived_source == "workout",
            Habit.active.is_(True),
        )
    )
    if workout_habit:
        local_day = session.completed_at.date()
        completion = db.scalar(
            select(HabitCompletion).where(
                HabitCompletion.habit_id == workout_habit.id,
                HabitCompletion.athlete_id == profile.id,
                HabitCompletion.local_date == local_day,
            )
        )
        if not completion:
            completion = HabitCompletion(
                habit_id=workout_habit.id,
                athlete_id=profile.id,
                local_date=local_day,
            )
            db.add(completion)
        completion.value = 1
        completion.completed = True
    grouped: dict[str, list[SetLog]] = defaultdict(list)
    for row in logs:
        grouped[row.prescribed_exercise_id].append(row)
    pr_count = 0
    proposals = []
    for prescription_id, current_sets in grouped.items():
        prescription = db.get(PrescribedExercise, prescription_id)
        previous_best = db.scalar(
            select(func.max(SetLog.load_kg))
            .join(WorkoutSession, SetLog.workout_session_id == WorkoutSession.id)
            .join(PrescribedExercise, SetLog.prescribed_exercise_id == PrescribedExercise.id)
            .where(
                WorkoutSession.athlete_id == profile.id,
                WorkoutSession.id != session.id,
                WorkoutSession.status == "completed",
                PrescribedExercise.exercise_id == prescription.exercise_id,
            )
        ) or 0
        current_best = max((row.load_kg or 0) for row in current_sets)
        if current_best > previous_best and current_best > 0:
            db.add(PersonalRecord(athlete_id=profile.id, exercise_id=prescription.exercise_id, workout_session_id=session.id, record_type="load", value=current_best))
            pr_count += 1
        achieved_top = bool(prescription.rep_max) and len(current_sets) >= prescription.target_sets and all(
            (row.reps or 0) >= prescription.rep_max and (row.rir is None or row.rir >= 1)
            for row in current_sets[: prescription.target_sets]
        )
        decision_type = "hold_plan"
        explanation = "Keep the current target while another comparable exposure is collected."
        confidence = 0.6
        if achieved_top:
            prior_top_sets = db.scalar(
                select(func.count(SetLog.id))
                .join(WorkoutSession, SetLog.workout_session_id == WorkoutSession.id)
                .join(PrescribedExercise, SetLog.prescribed_exercise_id == PrescribedExercise.id)
                .where(
                    WorkoutSession.athlete_id == profile.id,
                    WorkoutSession.id != session.id,
                    WorkoutSession.status == "completed",
                    PrescribedExercise.exercise_id == prescription.exercise_id,
                    SetLog.reps >= prescription.rep_max,
                    or_(SetLog.rir.is_(None), SetLog.rir >= 1),
                )
            ) or 0
            if prior_top_sets >= prescription.target_sets:
                decision_type = "increase_load"
                explanation = "You reached the top of the rep range with reserve across two exposures; a small load increase is appropriate next time."
                confidence = 0.86
        recommendation = RecommendationDecision(
            athlete_id=profile.id,
            decision_type=decision_type,
            evidence_snapshot={"session_id": session.id, "prescription_id": prescription_id, "sets": [{"load_kg": row.load_kg, "reps": row.reps, "rir": row.rir} for row in current_sets]},
            confidence=confidence,
            explanation=explanation,
            safety_checks=["ownership_validated", "session_completed", "no_pain_progression_signal"],
        )
        db.add(recommendation)
        proposals.append({"type": decision_type, "explanation": explanation})
    db.commit()
    summary = _session_payload(db, session)
    summary.update({"sets_completed": len(logs), "reps_completed": sum(row.reps or 0 for row in logs), "personal_records": pr_count, "recommendations": proposals})
    return {"summary": summary, "idempotent_replay": False}


@router.get("/workouts")
def workout_history(profile: AthleteProfile = Depends(current_profile), db: Session = Depends(get_db)):
    sessions = db.scalars(select(WorkoutSession).where(WorkoutSession.athlete_id == profile.id).order_by(WorkoutSession.started_at.desc()).limit(50)).all()
    return {"items": [_session_payload(db, session) for session in sessions]}

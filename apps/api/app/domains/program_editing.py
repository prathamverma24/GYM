from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import (
    AthleteProfile,
    Exercise,
    ExerciseSubstitutionGroup,
    PrescribedExercise,
    Program,
    ProgramDay,
    WorkoutDayTemplate,
    WorkoutPrescriptionTemplate,
    WorkoutSplitTemplate,
)


def _equipment_allowed(exercise: Exercise, inventory: list[str]) -> bool:
    if "full_gym" in inventory:
        return True
    allowed = set(inventory) | {"bodyweight"}
    options = exercise.equipment_options or [exercise.equipment]
    return any(set(option).issubset(allowed) for option in options)


def owned_active_program(db: Session, athlete_id: str, program_id: str) -> Program:
    program = db.scalar(
        select(Program).where(
            Program.id == program_id,
            Program.athlete_id == athlete_id,
            Program.status == "active",
        )
    )
    if not program:
        raise DomainError("ACTIVE_PROGRAM_NOT_FOUND", "The active training plan was not found.", 404)
    return program


def clone_active_program(
    db: Session,
    program: Program,
    edit_summary: str,
) -> tuple[Program, dict[str, ProgramDay], dict[str, PrescribedExercise]]:
    old_days = db.scalars(
        select(ProgramDay)
        .where(ProgramDay.program_id == program.id)
        .order_by(ProgramDay.day_index)
    ).all()
    db.execute(update(Program).where(Program.id == program.id).values(status="superseded"))
    rationale = [reason for reason in program.rationale if not str(reason).startswith("Customized:")]
    rationale.append(f"Customized: {edit_summary}")
    new_program = Program(
        athlete_id=program.athlete_id,
        name=program.name,
        status="active",
        generator_version="manual-v1",
        rationale=rationale,
        starts_on=program.starts_on,
    )
    db.add(new_program)
    db.flush()

    day_map: dict[str, ProgramDay] = {}
    prescription_map: dict[str, PrescribedExercise] = {}
    for old_day in old_days:
        new_day = ProgramDay(
            program_id=new_program.id,
            day_index=old_day.day_index,
            title=old_day.title,
            focus=list(old_day.focus),
            scheduled_date=old_day.scheduled_date,
            estimated_minutes=old_day.estimated_minutes,
        )
        db.add(new_day)
        db.flush()
        day_map[old_day.id] = new_day
        prescriptions = db.scalars(
            select(PrescribedExercise)
            .where(PrescribedExercise.program_day_id == old_day.id)
            .order_by(PrescribedExercise.order_index)
        ).all()
        for old_item in prescriptions:
            new_item = PrescribedExercise(
                program_day_id=new_day.id,
                exercise_id=old_item.exercise_id,
                order_index=old_item.order_index,
                target_sets=old_item.target_sets,
                rep_min=old_item.rep_min,
                rep_max=old_item.rep_max,
                target_seconds=old_item.target_seconds,
                rest_seconds=old_item.rest_seconds,
                target_rir=old_item.target_rir,
                notes=old_item.notes,
            )
            db.add(new_item)
            db.flush()
            prescription_map[old_item.id] = new_item
    return new_program, day_map, prescription_map


def activate_template(db: Session, profile: AthleteProfile, split_id: str) -> Program:
    split = db.get(WorkoutSplitTemplate, split_id)
    if not split:
        raise DomainError("PROGRAM_TEMPLATE_NOT_FOUND", "Workout plan template was not found.", 404)

    db.execute(
        update(Program)
        .where(Program.athlete_id == profile.id, Program.status == "active")
        .values(status="superseded")
    )
    program = Program(
        athlete_id=profile.id,
        name=split.name,
        status="active",
        generator_version=split.source_version,
        rationale=[
            split.description,
            f"{split.days_per_week} training days using the {split.approach_family.replace('_', ' ')} approach.",
            "Selected from the AthleteOS workout dataset; incompatible movements are replaced or omitted.",
        ],
        starts_on=date.today(),
    )
    db.add(program)
    db.flush()

    exercises = {
        exercise.source_id: exercise
        for exercise in db.scalars(
            select(Exercise).where(Exercise.published.is_(True), Exercise.source_id.is_not(None))
        ).all()
    }
    exercises_by_name = {exercise.name.casefold(): exercise for exercise in exercises.values()}
    substitution_groups = {
        group.source_id: group
        for group in db.scalars(select(ExerciseSubstitutionGroup)).all()
    }
    inventory = profile.equipment or ["bodyweight"]
    preferred_weekdays = profile.schedule.get("preferred_weekdays", [])
    estimated_minutes = int(profile.schedule.get("session_minutes", 60))
    cursor = date.today()
    day_templates = db.scalars(
        select(WorkoutDayTemplate)
        .where(WorkoutDayTemplate.split_source_id == split.source_id)
        .order_by(WorkoutDayTemplate.day_order)
    ).all()
    for day_template in day_templates:
        if preferred_weekdays:
            while cursor.weekday() not in preferred_weekdays:
                cursor += timedelta(days=1)
        day = ProgramDay(
            program_id=program.id,
            day_index=day_template.day_order,
            title=day_template.name,
            focus=[part.strip() for part in day_template.focus.replace("/", ",").split(",") if part.strip()],
            scheduled_date=cursor,
            estimated_minutes=estimated_minutes,
        )
        db.add(day)
        db.flush()
        templates = db.scalars(
            select(WorkoutPrescriptionTemplate)
            .where(WorkoutPrescriptionTemplate.day_template_source_id == day_template.source_id)
            .order_by(WorkoutPrescriptionTemplate.exercise_order)
        ).all()
        order_index = 1
        for item in templates:
            exercise = exercises.get(item.exercise_source_id)
            if exercise and not _equipment_allowed(exercise, inventory):
                group = substitution_groups.get(item.substitution_group_source_id or "")
                candidates = [group.default_exercise, *group.alternatives] if group else []
                exercise = next(
                    (
                        candidate
                        for name in candidates
                        if (candidate := exercises_by_name.get(name.casefold()))
                        and _equipment_allowed(candidate, inventory)
                    ),
                    None,
                )
            if not exercise or not _equipment_allowed(exercise, inventory):
                continue
            db.add(
                PrescribedExercise(
                    program_day_id=day.id,
                    exercise_id=exercise.id,
                    order_index=order_index,
                    target_sets=item.sets,
                    rep_min=item.rep_min,
                    rep_max=item.rep_max,
                    target_seconds=exercise.default_seconds,
                    rest_seconds=item.rest_seconds,
                    target_rir=item.target_rir,
                    notes=item.notes or "Technique takes priority over load.",
                )
            )
            order_index += 1
        cursor += timedelta(days=1)
    db.commit()
    db.refresh(program)
    return program


def add_day(
    db: Session,
    program: Program,
    *,
    title: str,
    focus: list[str],
    scheduled_date: date | None,
    estimated_minutes: int,
) -> tuple[Program, ProgramDay]:
    new_program, day_map, _ = clone_active_program(db, program, f"added {title}")
    day = ProgramDay(
        program_id=new_program.id,
        day_index=len(day_map) + 1,
        title=title,
        focus=focus,
        scheduled_date=scheduled_date,
        estimated_minutes=estimated_minutes,
    )
    db.add(day)
    db.commit()
    return new_program, day


def update_day(
    db: Session,
    program: Program,
    day_id: str,
    *,
    title: str,
    focus: list[str],
    scheduled_date: date | None,
    estimated_minutes: int,
) -> tuple[Program, ProgramDay]:
    new_program, day_map, _ = clone_active_program(db, program, f"updated {title}")
    day = day_map.get(day_id)
    if not day:
        raise DomainError("PROGRAM_DAY_NOT_FOUND", "Training day was not found.", 404)
    day.title = title
    day.focus = focus
    day.scheduled_date = scheduled_date
    day.estimated_minutes = estimated_minutes
    db.commit()
    return new_program, day


def remove_day(db: Session, program: Program, day_id: str) -> Program:
    current_days = db.scalars(select(ProgramDay).where(ProgramDay.program_id == program.id)).all()
    if len(current_days) <= 1:
        raise DomainError("PROGRAM_DAY_REQUIRED", "A training plan must keep at least one workout day.")
    old_day = next((day for day in current_days if day.id == day_id), None)
    if not old_day:
        raise DomainError("PROGRAM_DAY_NOT_FOUND", "Training day was not found.", 404)
    new_program, day_map, _ = clone_active_program(db, program, f"removed {old_day.title}")
    day = day_map[day_id]
    db.execute(delete(PrescribedExercise).where(PrescribedExercise.program_day_id == day.id))
    db.delete(day)
    db.flush()
    remaining = db.scalars(
        select(ProgramDay)
        .where(ProgramDay.program_id == new_program.id)
        .order_by(ProgramDay.day_index)
    ).all()
    for index, item in enumerate(remaining, 1):
        item.day_index = index
    new_program.name = _custom_program_name(new_program.name, len(remaining))
    db.commit()
    return new_program


def add_exercise(
    db: Session,
    program: Program,
    day_id: str,
    exercise: Exercise,
    values: dict,
) -> tuple[Program, ProgramDay, PrescribedExercise]:
    new_program, day_map, _ = clone_active_program(db, program, f"added {exercise.name}")
    day = day_map.get(day_id)
    if not day:
        raise DomainError("PROGRAM_DAY_NOT_FOUND", "Training day was not found.", 404)
    existing = db.scalars(
        select(PrescribedExercise).where(PrescribedExercise.program_day_id == day.id)
    ).all()
    if any(item.exercise_id == exercise.id for item in existing):
        raise DomainError("EXERCISE_ALREADY_PLANNED", "That exercise is already in this workout.")
    item = PrescribedExercise(
        program_day_id=day.id,
        exercise_id=exercise.id,
        order_index=len(existing) + 1,
        **_prescription_values(exercise, values),
    )
    db.add(item)
    db.commit()
    return new_program, day, item


def update_exercise(
    db: Session,
    program: Program,
    day_id: str,
    prescribed_exercise_id: str,
    exercise: Exercise,
    values: dict,
) -> tuple[Program, ProgramDay, PrescribedExercise]:
    new_program, day_map, prescription_map = clone_active_program(
        db, program, f"updated {exercise.name}"
    )
    day = day_map.get(day_id)
    item = prescription_map.get(prescribed_exercise_id)
    if not day or not item or item.program_day_id != day.id:
        raise DomainError("PRESCRIBED_EXERCISE_NOT_FOUND", "Planned exercise was not found.", 404)
    siblings = db.scalars(
        select(PrescribedExercise)
        .where(PrescribedExercise.program_day_id == day.id, PrescribedExercise.id != item.id)
        .order_by(PrescribedExercise.order_index)
    ).all()
    if any(sibling.exercise_id == exercise.id for sibling in siblings):
        raise DomainError("EXERCISE_ALREADY_PLANNED", "That exercise is already in this workout.")
    item.exercise_id = exercise.id
    for key, value in _prescription_values(exercise, values).items():
        setattr(item, key, value)
    desired_index = max(1, min(int(values.get("order_index", item.order_index)), len(siblings) + 1))
    ordered = list(siblings)
    ordered.insert(desired_index - 1, item)
    for index, sibling in enumerate(ordered, 1):
        sibling.order_index = index
    db.commit()
    return new_program, day, item


def remove_exercise(
    db: Session,
    program: Program,
    day_id: str,
    prescribed_exercise_id: str,
) -> tuple[Program, ProgramDay]:
    current_items = db.scalars(
        select(PrescribedExercise).where(PrescribedExercise.program_day_id == day_id)
    ).all()
    if len(current_items) <= 1:
        raise DomainError("EXERCISE_REQUIRED", "A workout must keep at least one exercise.")
    old_item = next((item for item in current_items if item.id == prescribed_exercise_id), None)
    if not old_item:
        raise DomainError("PRESCRIBED_EXERCISE_NOT_FOUND", "Planned exercise was not found.", 404)
    exercise = db.get(Exercise, old_item.exercise_id)
    new_program, day_map, prescription_map = clone_active_program(
        db, program, f"removed {exercise.name if exercise else 'an exercise'}"
    )
    day = day_map[day_id]
    db.delete(prescription_map[prescribed_exercise_id])
    db.flush()
    remaining = db.scalars(
        select(PrescribedExercise)
        .where(PrescribedExercise.program_day_id == day.id)
        .order_by(PrescribedExercise.order_index)
    ).all()
    for index, item in enumerate(remaining, 1):
        item.order_index = index
    db.commit()
    return new_program, day


def _prescription_values(exercise: Exercise, values: dict) -> dict:
    return {
        "target_sets": values.get("target_sets") or exercise.default_sets,
        "rep_min": values.get("rep_min") if values.get("rep_min") is not None else exercise.default_rep_min,
        "rep_max": values.get("rep_max") if values.get("rep_max") is not None else exercise.default_rep_max,
        "target_seconds": values.get("target_seconds") if values.get("target_seconds") is not None else exercise.default_seconds,
        "rest_seconds": values.get("rest_seconds") or exercise.rest_seconds,
        "target_rir": values.get("target_rir") if values.get("target_rir") is not None else 2,
        "notes": values.get("notes") or "Technique takes priority over load.",
    }


def _custom_program_name(name: str, days: int) -> str:
    if "·" in name and name.rstrip().endswith("days"):
        return f"{name.rsplit('·', 1)[0].strip()} · {days} days"
    return name

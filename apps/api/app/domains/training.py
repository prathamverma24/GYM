from datetime import date, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import (
    AthleteProfile,
    Exercise,
    Habit,
    PrescribedExercise,
    Program,
    ProgramDay,
)

SPLITS = {
    "bodybuilding": {
        3: [("Full Body A", ["chest", "back", "legs"]), ("Full Body B", ["back", "shoulders", "legs"]), ("Full Body C", ["chest", "arms", "legs"])],
        4: [("Upper Strength", ["chest", "back"]), ("Lower Strength", ["legs", "core"]), ("Upper Hypertrophy", ["shoulders", "arms"]), ("Lower Hypertrophy", ["legs", "core"])],
        5: [("Push Day", ["chest", "shoulders", "triceps"]), ("Pull Day", ["back", "biceps"]), ("Leg Day", ["legs", "core"]), ("Upper Aesthetic", ["shoulders", "chest", "back"]), ("Lower & Core", ["legs", "core"])],
        6: [("Push A", ["chest", "shoulders"]), ("Pull A", ["back", "biceps"]), ("Legs A", ["legs"]), ("Push B", ["chest", "triceps"]), ("Pull B", ["back", "biceps"]), ("Legs B", ["legs", "core"])],
    },
    "aesthetic": {
        3: [("V-Taper Full Body", ["shoulders", "back", "legs"]), ("Upper Shape", ["chest", "shoulders", "arms"]), ("Lower Balance", ["legs", "core"])],
        5: [("Shoulders & Upper Chest", ["shoulders", "chest"]), ("Back Width", ["back", "biceps"]), ("Leg Shape", ["legs"]), ("Arms & Delts", ["shoulders", "arms"]), ("Balanced Full Body", ["chest", "back", "legs", "core"])],
    },
    "calisthenics": {
        3: [("Push Foundations", ["chest", "shoulders", "triceps"]), ("Pull Foundations", ["back", "biceps"]), ("Skill & Legs", ["core", "legs", "shoulders"])],
        5: [("Push Skill", ["chest", "shoulders"]), ("Pull Skill", ["back", "biceps"]), ("Legs & Core", ["legs", "core"]), ("Handstand Practice", ["shoulders", "core"]), ("Strength Skills", ["back", "chest", "core"])],
    },
    "athletic": {
        3: [("Total-Body Strength", ["legs", "back", "chest"]), ("Speed & Power", ["conditioning", "legs"]), ("Strength & Capacity", ["full body", "core"])],
        5: [("Lower Strength", ["legs"]), ("Acceleration", ["conditioning"]), ("Upper Strength", ["chest", "back"]), ("Power", ["full body", "legs"]), ("Conditioning & Core", ["conditioning", "core"])],
    },
    "hybrid": {
        3: [("Strength Base", ["chest", "back", "legs"]), ("Skills & Power", ["shoulders", "core", "conditioning"]), ("Hypertrophy Mix", ["shoulders", "back", "legs"])],
        5: [("Push Strength", ["chest", "shoulders"]), ("Pull Skill", ["back", "biceps"]), ("Lower Strength", ["legs"]), ("Athletic Power", ["conditioning", "full body"]), ("Aesthetic Volume", ["shoulders", "arms", "core"])],
    },
}

DAY_SLUGS = {
    "push": ["barbell-bench-press", "incline-dumbbell-press", "standing-shoulder-press", "dumbbell-lateral-raise", "cable-triceps-pushdown", "push-up"],
    "pull": ["lat-pulldown", "pull-up", "seated-cable-row", "one-arm-dumbbell-row", "barbell-curl", "dumbbell-curl"],
    "leg": ["back-squat", "goblet-squat", "romanian-deadlift", "dumbbell-romanian-deadlift", "walking-lunge", "standing-calf-raise", "forearm-plank"],
    "speed": ["acceleration-sprint", "box-jump", "goblet-squat", "farmer-carry", "forearm-plank"],
    "power": ["box-jump", "kettlebell-swing", "back-squat", "farmer-carry", "forearm-plank"],
    "skill": ["dead-hang", "assisted-pull-up", "pull-up", "wall-handstand-hold", "l-sit-tuck-hold", "reverse-lunge"],
    "full": ["goblet-squat", "push-up", "one-arm-dumbbell-row", "dumbbell-romanian-deadlift", "dumbbell-lateral-raise", "forearm-plank"],
    "upper": ["barbell-bench-press", "lat-pulldown", "incline-dumbbell-press", "seated-cable-row", "dumbbell-lateral-raise", "dumbbell-curl"],
}


def _nearest_days(mapping: dict, requested: int) -> list:
    key = min(mapping, key=lambda candidate: abs(candidate - requested))
    return mapping[key]


def _equipment_allowed(exercise: Exercise, inventory: list[str]) -> bool:
    if "full_gym" in inventory:
        return True
    allowed = set(inventory) | {"bodyweight"}
    options = exercise.equipment_options or [exercise.equipment]
    return any(set(option).issubset(allowed) for option in options)


def _template_key(title: str) -> str:
    lowered = title.lower()
    for key in ("push", "pull", "leg", "speed", "power", "skill", "upper"):
        if key in lowered:
            return key
    return "full"


def generate_program(db: Session, profile: AthleteProfile) -> Program:
    if not all((profile.training_type, profile.experience_level, profile.primary_goal)):
        raise DomainError("ONBOARDING_INCOMPLETE", "Complete the training profile before generating a plan.")
    days = max(2, min(6, int(profile.schedule.get("days_per_week", 3))))
    mode = profile.training_type
    mapping = SPLITS.get(mode, SPLITS["hybrid"])
    split = _nearest_days(mapping, days)
    db.execute(
        update(Program)
        .where(Program.athlete_id == profile.id, Program.status == "active")
        .values(status="superseded")
    )
    today = date.today()
    program = Program(
        athlete_id=profile.id,
        name=f"{profile.experience_level.title()} {mode.title()} · {len(split)} days",
        starts_on=today,
        rationale=[
            f"Built for {mode} with a {profile.primary_goal.replace('_', ' ')} priority.",
            f"Uses {len(split)} sessions within about {profile.schedule.get('session_minutes', 60)} minutes.",
            "Exercises are filtered to your recorded equipment.",
        ],
    )
    db.add(program)
    db.flush()
    exercises = {item.slug: item for item in db.scalars(select(Exercise).where(Exercise.published.is_(True))).all()}
    inventory = profile.equipment or ["bodyweight"]
    requested_dates = profile.schedule.get("preferred_weekdays", [])
    cursor = today
    for index, (title, focus) in enumerate(split, 1):
        if requested_dates:
            while cursor.weekday() not in requested_dates:
                cursor += timedelta(days=1)
        day = ProgramDay(
            program_id=program.id,
            day_index=index,
            title=title,
            focus=focus,
            scheduled_date=cursor,
            estimated_minutes=int(profile.schedule.get("session_minutes", 60)),
        )
        db.add(day)
        db.flush()
        candidates = DAY_SLUGS[_template_key(title)]
        selected = [exercises[slug] for slug in candidates if slug in exercises and _equipment_allowed(exercises[slug], inventory)]
        if len(selected) < 4:
            fallback = [e for e in exercises.values() if _equipment_allowed(e, inventory) and mode in e.training_types]
            for exercise in fallback:
                if exercise not in selected:
                    selected.append(exercise)
                if len(selected) >= 5:
                    break
        level_sets_delta = 1 if profile.experience_level == "advanced" else 0
        for order, exercise in enumerate(selected[:6], 1):
            db.add(
                PrescribedExercise(
                    program_day_id=day.id,
                    exercise_id=exercise.id,
                    order_index=order,
                    target_sets=min(5, exercise.default_sets + level_sets_delta),
                    rep_min=exercise.default_rep_min,
                    rep_max=exercise.default_rep_max,
                    target_seconds=exercise.default_seconds,
                    rest_seconds=exercise.rest_seconds,
                    target_rir=2 if profile.experience_level in {"beginner", "early_beginner"} else 1,
                    notes="Leave the target reps in reserve; technique takes priority.",
                )
            )
        cursor += timedelta(days=1)
    if not db.scalar(select(Habit).where(Habit.athlete_id == profile.id)):
        defaults = [
            ("Complete planned training", "training", "workout"),
            (f"Drink {round((profile.water_target_ml or 3000) / 1000, 1)} L water", "hydration", "water"),
            ("Sleep 7+ hours", "recovery", None),
            ("Mobility 10 minutes", "mobility", None),
        ]
        for name, category, source in defaults:
            db.add(Habit(athlete_id=profile.id, name=name, category=category, derived_source=source))
    db.commit()
    db.refresh(program)
    return program

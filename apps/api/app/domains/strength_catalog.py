from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Exercise,
    ExerciseMuscleMapping,
    ExerciseProgression,
    MuscleGroup,
    new_id,
)

MUSCLE_GROUPS = (
    ("Chest", "chest", "upper", 10),
    ("Upper Chest", "upper-chest", "upper", 20),
    ("Lats", "lats", "upper", 30),
    ("Upper Back", "upper-back", "upper", 40),
    ("Traps", "traps", "upper", 50),
    ("Front Delts", "front-delts", "upper", 60),
    ("Side Delts", "side-delts", "upper", 70),
    ("Rear Delts", "rear-delts", "upper", 80),
    ("Biceps", "biceps", "upper", 90),
    ("Triceps", "triceps", "upper", 100),
    ("Forearms", "forearms", "upper", 110),
    ("Core", "core", "core", 120),
    ("Lower Back", "lower-back", "core", 130),
    ("Glutes", "glutes", "lower", 140),
    ("Quadriceps", "quadriceps", "lower", 150),
    ("Hamstrings", "hamstrings", "lower", 160),
    ("Calves", "calves", "lower", 170),
    ("Adductors", "adductors", "lower", 180),
    ("Hip Flexors", "hip-flexors", "lower", 190),
)

PROGRESSION_GROUPS: dict[str, list[tuple[str, float]]] = {
    "pull-up": [
        ("assisted-pull-up", 1.0),
        ("negative-pull-up", 1.3),
        ("scapular-pull-up", 1.45),
        ("pull-up", 1.8),
        ("chin-up", 1.85),
    ],
    "dip": [("assisted-dip", 1.0), ("chest-dip", 1.8)],
    "handstand-push": [
        ("pike-push-up", 1.0),
        ("elevated-pike-push-up", 1.35),
        ("wall-handstand-hold", 1.55),
        ("wall-handstand-push-up", 2.2),
    ],
    "l-sit": [("tuck-l-sit", 1.0), ("l-sit", 1.8)],
    "front-lever": [
        ("tuck-front-lever-hold", 1.0),
        ("advanced-tuck-front-lever-hold", 1.5),
    ],
    "planche": [("planche-lean", 1.0), ("tuck-planche-hold", 1.7)],
    "muscle-up": [("band-assisted-muscle-up", 1.0), ("muscle-up", 2.0)],
    "pistol-squat": [("assisted-pistol-squat", 1.0), ("pistol-squat", 1.8)],
}


def _normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def normalize_muscle_label(label: str) -> list[tuple[str, float]]:
    """Translate dataset labels to normalized reporting muscles.

    The float is a multiplier used for broad source labels. The role weight is
    applied separately, so a primary Chest mapping remains 1.0 while a broad
    Total Body mapping is deliberately distributed.
    """

    value = _normal(label)
    if not value:
        return []
    direct_rules = (
        (("upper chest",), [("upper-chest", 1.0)]),
        (("chest",), [("chest", 1.0)]),
        (("lat", "scapular depressor"), [("lats", 1.0)]),
        (("upper back",), [("upper-back", 1.0)]),
        (("trap",), [("traps", 1.0)]),
        (("front delt",), [("front-delts", 1.0)]),
        (("side delt",), [("side-delts", 1.0)]),
        (("rear delt",), [("rear-delts", 1.0)]),
        (("brachioradialis",), [("forearms", 1.0)]),
        (("biceps", "brachialis"), [("biceps", 1.0)]),
        (("triceps",), [("triceps", 1.0)]),
        (("forearm", "wrist", "grip"), [("forearms", 1.0)]),
        (("abs", "core", "oblique"), [("core", 1.0)]),
        (("erector", "lower back"), [("lower-back", 1.0)]),
        (("glute", "hip extension", "hips"), [("glutes", 1.0)]),
        (("quad",), [("quadriceps", 1.0)]),
        (("hamstring",), [("hamstrings", 1.0)]),
        (("calf", "calves", "gastrocnemius", "soleus", "ankle"), [("calves", 1.0)]),
        (("adductor",), [("adductors", 1.0)]),
        (("hip flexor",), [("hip-flexors", 1.0)]),
    )
    for needles, targets in direct_rules:
        if any(needle in value for needle in needles):
            return targets
    if value == "front":
        return [("front-delts", 1.0)]
    if value in {"shoulder", "shoulders"}:
        return [("front-delts", 0.8), ("side-delts", 0.8)]
    if value in {"leg", "legs", "lower body", "lower body power"}:
        return [("quadriceps", 0.7), ("glutes", 0.7), ("hamstrings", 0.55)]
    if "total body" in value or "rotational power" in value:
        return [
            ("core", 0.5),
            ("glutes", 0.5),
            ("quadriceps", 0.45),
            ("upper-back", 0.35),
        ]
    return []


def exercise_contributions(exercise: Exercise) -> list[tuple[str, str, float]]:
    collected: dict[str, tuple[str, float]] = {}
    for role, base, labels in (
        ("PRIMARY", 1.0, exercise.primary_muscles or []),
        ("SECONDARY", 0.35, exercise.secondary_muscles or []),
    ):
        for label in labels:
            for slug, multiplier in normalize_muscle_label(label):
                weight = round(base * multiplier, 3)
                current = collected.get(slug)
                if current is None or weight > current[1]:
                    collected[slug] = (role, weight)
    if not collected:
        for slug, multiplier in normalize_muscle_label(exercise.category):
            collected[slug] = ("PRIMARY", multiplier)
    if not collected:
        pattern = exercise.movement_pattern
        if "push" in pattern:
            collected["chest"] = ("PRIMARY", 0.7)
            collected["triceps"] = ("SECONDARY", 0.35)
        elif "pull" in pattern:
            collected["upper-back"] = ("PRIMARY", 0.7)
            collected["biceps"] = ("SECONDARY", 0.35)
        elif any(term in pattern for term in ("squat", "lunge", "jump")):
            collected["quadriceps"] = ("PRIMARY", 0.7)
            collected["glutes"] = ("PRIMARY", 0.7)
        elif "hinge" in pattern:
            collected["hamstrings"] = ("PRIMARY", 0.7)
            collected["glutes"] = ("PRIMARY", 0.7)
        else:
            collected["core"] = ("PRIMARY", 0.5)
    return [(slug, role, weight) for slug, (role, weight) in collected.items()]


def seed_strength_catalogue(db: Session) -> None:
    groups_by_slug = {
        group.slug: group for group in db.scalars(select(MuscleGroup)).all()
    }
    for name, slug, region, order in MUSCLE_GROUPS:
        group = groups_by_slug.get(slug)
        if group is None:
            group = MuscleGroup(
                id=new_id(), name=name, slug=slug, body_region=region, sort_order=order
            )
            db.add(group)
            groups_by_slug[slug] = group
        else:
            group.name = name
            group.body_region = region
            group.sort_order = order
    db.flush()

    exercises = db.scalars(select(Exercise).where(Exercise.published.is_(True))).all()
    existing_mappings = {
        (row.exercise_id, row.muscle_group_id): row
        for row in db.scalars(select(ExerciseMuscleMapping)).all()
    }
    expected_keys: set[tuple[str, str]] = set()
    for exercise in exercises:
        for muscle_slug, role, weight in exercise_contributions(exercise):
            group = groups_by_slug[muscle_slug]
            key = (exercise.id, group.id)
            expected_keys.add(key)
            mapping = existing_mappings.get(key)
            if mapping is None:
                db.add(
                    ExerciseMuscleMapping(
                        id=new_id(),
                        exercise_id=exercise.id,
                        muscle_group_id=group.id,
                        role=role,
                        contribution_weight=weight,
                    )
                )
            else:
                mapping.role = role
                mapping.contribution_weight = weight
    for key, mapping in existing_mappings.items():
        if key not in expected_keys:
            db.delete(mapping)

    exercises_by_slug = {exercise.slug: exercise for exercise in exercises}
    existing_progressions = {
        row.exercise_id: row for row in db.scalars(select(ExerciseProgression)).all()
    }
    expected_progressions: set[str] = set()
    for group_name, levels in PROGRESSION_GROUPS.items():
        available = [(exercises_by_slug.get(slug), multiplier) for slug, multiplier in levels]
        available = [(exercise, multiplier) for exercise, multiplier in available if exercise]
        for index, (exercise, multiplier) in enumerate(available):
            expected_progressions.add(exercise.id)
            progression = existing_progressions.get(exercise.id)
            values = {
                "progression_group": group_name,
                "level": float(index + 1),
                "previous_exercise_id": available[index - 1][0].id if index else None,
                "next_exercise_id": available[index + 1][0].id
                if index + 1 < len(available)
                else None,
                "difficulty_multiplier": multiplier,
            }
            if progression is None:
                db.add(ExerciseProgression(id=new_id(), exercise_id=exercise.id, **values))
            else:
                for field, value in values.items():
                    setattr(progression, field, value)
    for exercise_id, progression in existing_progressions.items():
        if exercise_id not in expected_progressions:
            db.delete(progression)
    db.commit()

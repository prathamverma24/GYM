from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path
from statistics import median
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Exercise,
    ExerciseSubstitutionGroup,
    ProgramSelectionRule,
    ProgressionRuleDefinition,
    ResearchSource,
    WorkoutDayTemplate,
    WorkoutPrescriptionTemplate,
    WorkoutSplitTemplate,
)

DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "workout_dataset_v1.json"
DATASET_VERSION = "dataset-v1.0"
LEGACY_EXERCISE_SLUGS = {
    "cable-triceps-pushdown",
    "dead-hang",
    "dumbbell-curl",
    "forearm-plank",
    "knee-push-up",
    "l-sit-tuck-hold",
    "parallel-bar-dip",
    "standing-shoulder-press",
}


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def _items(value: str | None, separator: str = ";") -> list[str]:
    return [item.strip() for item in str(value or "").split(separator) if item.strip()]


def _normalized_items(value: str | None) -> list[str]:
    return [_slug(item).replace("-", "_") for item in _items(value)]


def _equipment_token(value: str) -> str:
    normalized = _slug(value).replace("-", " ")
    rules = (
        ("pull up bar", "pull_up_bar"),
        ("dumbbell", "dumbbells"),
        ("kettlebell", "kettlebells"),
        ("barbell", "barbell"),
        ("ez bar", "ez_bar"),
        ("resistance band", "resistance_bands"),
        ("band", "resistance_bands"),
        ("cable", "cable_machine"),
        ("incline bench", "bench"),
        ("preacher bench", "preacher_bench"),
        ("nordic bench", "nordic_bench"),
        ("back extension bench", "back_extension_bench"),
        ("bench", "bench"),
        ("squat rack", "squat_rack"),
        ("rack", "squat_rack"),
        ("smith machine", "smith_machine"),
        ("hack squat machine", "hack_squat_machine"),
        ("leg press", "leg_press_machine"),
        ("assisted machine", "assisted_machine"),
        ("reverse pec deck", "reverse_pec_deck"),
        ("pec deck", "pec_deck"),
        ("machine", "machine"),
        ("bodyweight", "bodyweight"),
        ("gymnastic rings", "rings"),
        ("rings", "rings"),
        ("trx", "suspension_trainer"),
        ("dip bars", "dip_bars"),
        ("parallettes", "parallettes"),
        ("box", "plyo_box"),
        ("medicine ball", "medicine_ball"),
        ("landmine", "landmine"),
        ("trap bar", "trap_bar"),
        ("bar", "pull_up_bar"),
        ("sled", "sled"),
        ("track", "open_space"),
        ("turf", "open_space"),
        ("cones", "open_space"),
        ("wall", "wall"),
        ("support", "bodyweight"),
        ("treadmill", "treadmill"),
        ("row ergometer", "rower"),
        ("air bike", "stationary_bike"),
        ("stationary bike", "stationary_bike"),
        ("jump rope", "jump_rope"),
        ("ab wheel", "ab_wheel"),
    )
    for needle, token in rules:
        if needle in normalized:
            return token
    return _slug(value).replace("-", "_")


def equipment_options(value: str) -> list[list[str]]:
    options = []
    for alternative in value.split("/"):
        required = []
        for component in alternative.split("+"):
            token = _equipment_token(component.strip())
            if token and token not in required:
                required.append(token)
        if required and required not in options:
            options.append(required)
    return options or [["bodyweight"]]


def _flat_equipment(options: list[list[str]]) -> list[str]:
    return list(dict.fromkeys(token for option in options for token in option))


def _modality(metric: str, options: list[list[str]], name: str) -> str:
    if metric == "seconds":
        return "isometric_hold"
    if metric == "meters":
        return "distance_time"
    if metric == "minutes":
        return "duration"
    if "assisted" in name.lower():
        return "assisted_reps"
    bodyweight_tools = {
        "bodyweight",
        "pull_up_bar",
        "rings",
        "dip_bars",
        "parallettes",
        "plyo_box",
        "wall",
        "suspension_trainer",
    }
    if all(set(option).issubset(bodyweight_tools) for option in options):
        return "bodyweight_reps"
    return "weighted_reps"


def _instruction(row: dict[str, Any]) -> str:
    if row.get("coaching_note"):
        return str(row["coaching_note"])
    pattern = str(row["movement_pattern"]).lower()
    equipment = str(row["equipment"])
    return (
        f"Set up securely for {row['name']} using {equipment}. Perform the {pattern} pattern "
        "through a controlled, comfortable range while keeping the target muscles loaded and each repetition repeatable."
    )


def _safety_note(row: dict[str, Any]) -> str:
    pattern = str(row["movement_pattern"]).lower()
    if any(term in pattern for term in ("jump", "sprint", "power", "ballistic", "olympic")):
        return "Use a clear training area and stop the set when speed, landing, or catch quality declines."
    if "skill" in pattern or row["category"] == "Calisthenics Skill":
        return "Use an appropriate progression and stable supports; never force range or hold time when joint control is lost."
    if row["is_unilateral"]:
        return "Use stable support when needed, keep both sides controlled, and stop for sharp pain or loss of balance."
    return "Use a load you can control, keep joints in a comfortable path, and stop if you feel sharp pain."


@lru_cache(maxsize=1)
def load_workout_dataset() -> dict[str, Any]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def _upsert(
    db: Session,
    model: type,
    key: str,
    values: dict[str, Any],
    existing: dict[str, Any] | None = None,
):
    row = existing.get(key) if existing is not None else db.get(model, key)
    if row is None:
        row = model(source_id=key, **values)
        db.add(row)
        if existing is not None:
            existing[key] = row
    else:
        for field, value in values.items():
            setattr(row, field, value)
    return row


def seed_workout_dataset(db: Session) -> None:
    dataset = load_workout_dataset()
    sheets = dataset["sheets"]
    counts = dataset["metadata"]["counts"]
    catalogue_is_current = (
        db.scalar(
            select(func.count())
            .select_from(Exercise)
            .where(Exercise.source_version == DATASET_VERSION)
        )
        == counts["Exercise_Catalog"]
        and db.scalar(select(func.count()).select_from(WorkoutPrescriptionTemplate))
        == counts["Day_Exercises"]
        and db.scalar(select(func.count()).select_from(ResearchSource))
        == counts["Research_Sources"]
    )
    if catalogue_is_current:
        return

    prescriptions_by_exercise: dict[str, list[int]] = defaultdict(list)
    for prescription in sheets["Day_Exercises"]:
        prescriptions_by_exercise[prescription["exercise_id"]].append(int(prescription["sets"]))

    existing_exercises = db.scalars(select(Exercise)).all()
    existing_by_slug = {exercise.slug: exercise for exercise in existing_exercises}
    existing_by_source = {
        exercise.source_id: exercise for exercise in existing_exercises if exercise.source_id
    }
    for source in sheets["Exercise_Catalog"]:
        slug = _slug(source["name"])
        exercise = existing_by_source.get(source["exercise_id"])
        if exercise is None:
            exercise = existing_by_slug.get(slug)
        if exercise is None:
            exercise = Exercise(name=source["name"], slug=slug)
            db.add(exercise)
        existing_by_source[source["exercise_id"]] = exercise
        existing_by_slug[slug] = exercise
        options = equipment_options(source["equipment"])
        metric = str(source["tracking_metric"]).lower()
        observed_sets = prescriptions_by_exercise[source["exercise_id"]]
        exercise.source_id = source["exercise_id"]
        exercise.name = source["name"]
        exercise.slug = slug
        exercise.category = source["category"]
        exercise.primary_muscles = _items(source["primary_muscle"], "/")
        exercise.secondary_muscles = _items(source.get("secondary_muscles"))
        exercise.movement_pattern = _slug(source["movement_pattern"]).replace("-", "_")
        exercise.equipment = _flat_equipment(options)
        exercise.equipment_display = source["equipment"]
        exercise.equipment_options = options
        exercise.difficulty = str(source["difficulty"]).lower()
        exercise.training_types = _normalized_items(source["athlete_types"])
        exercise.is_compound = bool(source["is_compound"])
        exercise.is_unilateral = bool(source["is_unilateral"])
        exercise.tracking_metric = metric
        exercise.minimum_level = _slug(source["minimum_level"]).replace("-", "_")
        exercise.modality = _modality(metric, options, source["name"])
        exercise.instructions = _instruction(source)
        exercise.safety_notes = _safety_note(source)
        exercise.default_sets = round(median(observed_sets)) if observed_sets else 3
        exercise.default_rep_min = int(source["default_rep_min"])
        exercise.default_rep_max = int(source["default_rep_max"])
        exercise.default_seconds = (
            int(source["default_rep_min"]) if metric == "seconds" else None
        )
        exercise.rest_seconds = int(source["default_rest_sec"])
        exercise.source_version = DATASET_VERSION
        exercise.source_metadata = {
            "source_category": source["category"],
            "source_movement_pattern": source["movement_pattern"],
            "source_equipment": source["equipment"],
        }
        exercise.version = dataset["metadata"]["version"]
        exercise.published = True
    for legacy in existing_exercises:
        if legacy.source_id is None and legacy.slug in LEGACY_EXERCISE_SLUGS:
            legacy.published = False
    db.flush()

    progression_rules = {
        row.source_id: row for row in db.scalars(select(ProgressionRuleDefinition)).all()
    }
    for source in sheets["Progression_Rules"]:
        _upsert(
            db,
            ProgressionRuleDefinition,
            source["rule_id"],
            {
                "name": source["name"],
                "applies_to": source["applies_to"],
                "trigger": source["trigger"],
                "action": source["action"],
                "regression": source["regression"],
                "notes": source["notes"],
            },
            progression_rules,
        )
    substitution_groups = {
        row.source_id: row for row in db.scalars(select(ExerciseSubstitutionGroup)).all()
    }
    for source in sheets["Substitutions"]:
        _upsert(
            db,
            ExerciseSubstitutionGroup,
            source["group_id"],
            {
                "name": source["group_name"],
                "default_exercise": source["default_exercise"],
                "alternatives": _items(source["alternatives"]),
                "logic": source["logic"],
            },
            substitution_groups,
        )
    split_templates = {
        row.source_id: row for row in db.scalars(select(WorkoutSplitTemplate)).all()
    }
    for source in sheets["Split_Templates"]:
        _upsert(
            db,
            WorkoutSplitTemplate,
            source["split_id"],
            {
                "name": source["split_name"],
                "approach_family": source["approach_family"],
                "days_per_week": int(source["days_per_week"]),
                "experience_min": source["experience_min"],
                "experience_max": source["experience_max"],
                "primary_goals": _items(source["primary_goals"]),
                "athlete_types": _items(source["athlete_types"]),
                "typical_muscle_frequency": source["typical_muscle_frequency"],
                "weekly_set_guardrails": {
                    "beginner": source["weekly_set_guardrail_beginner"],
                    "intermediate": source["weekly_set_guardrail_intermediate"],
                    "advanced": source["weekly_set_guardrail_advanced"],
                },
                "session_minutes": source["session_minutes"],
                "equipment_requirement": source["equipment_requirement"],
                "recovery_demand": source["recovery_demand"],
                "schedule_pattern": source["schedule_pattern"],
                "day_blueprints": _items(source["day_blueprints"]),
                "description": source["description"],
                "source_version": DATASET_VERSION,
            },
            split_templates,
        )
    db.flush()
    day_templates = {
        row.source_id: row for row in db.scalars(select(WorkoutDayTemplate)).all()
    }
    for source in sheets["Program_Days"]:
        _upsert(
            db,
            WorkoutDayTemplate,
            source["day_template_id"],
            {
                "split_source_id": source["split_id"],
                "day_order": int(source["day_order"]),
                "blueprint_code": source["blueprint_code"],
                "name": source["day_name"],
                "focus": source["focus"],
                "recommended_after_day": source["recommended_after_day"],
                "is_optional": bool(source["is_optional"]),
            },
            day_templates,
        )
    db.flush()
    prescription_templates = {
        row.source_id: row
        for row in db.scalars(select(WorkoutPrescriptionTemplate)).all()
    }
    for source in sheets["Day_Exercises"]:
        _upsert(
            db,
            WorkoutPrescriptionTemplate,
            source["prescription_id"],
            {
                "day_template_source_id": source["day_template_id"],
                "exercise_source_id": source["exercise_id"],
                "exercise_name": source["exercise_name"],
                "exercise_order": int(source["exercise_order"]),
                "sets": int(source["sets"]),
                "rep_min": int(source["rep_min"]),
                "rep_max": int(source["rep_max"]),
                "target_rir": int(source["target_rir"]),
                "rest_seconds": int(source["rest_sec"]),
                "progression_rule_source_id": source["progression_rule_id"],
                "substitution_group_source_id": source["substitution_group_id"],
                "is_optional": bool(source["optional"]),
                "notes": source["notes"],
            },
            prescription_templates,
        )
    selection_rules = {
        row.source_id: row for row in db.scalars(select(ProgramSelectionRule)).all()
    }
    for source in sheets["Selection_Rules"]:
        _upsert(
            db,
            ProgramSelectionRule,
            source["rule_id"],
            {
                "days_min": int(source["days_min"]),
                "days_max": int(source["days_max"]),
                "level": source["level"],
                "goal": source["goal"],
                "equipment": source["equipment"],
                "athlete_type": source["athlete_type"],
                "recommended_splits": _items(source["recommended_splits"]),
                "priority": int(source["priority"]),
                "reason": source["reason"],
            },
            selection_rules,
        )
    research_sources = {
        row.source_id: row for row in db.scalars(select(ResearchSource)).all()
    }
    for source in sheets["Research_Sources"]:
        _upsert(
            db,
            ResearchSource,
            source["source_id"],
            {
                "topic": source["topic"],
                "evidence_summary": source["evidence_summary"],
                "url": source["url"],
                "accessed": date.fromisoformat(source["accessed"]),
            },
            research_sources,
        )
    db.commit()

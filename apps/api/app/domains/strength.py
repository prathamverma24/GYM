from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from statistics import fmean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BodyMetricEntry,
    Exercise,
    ExerciseMuscleMapping,
    ExerciseProgression,
    MuscleGroup,
    PrescribedExercise,
    SetLog,
    WorkoutSession,
)

ANALYTICS_VERSION = "strength_v1"
SUPPORTED_PERIODS = {"week", "month", "3_months"}


@dataclass(frozen=True)
class PeriodWindow:
    period_type: str
    start: date
    end: date
    expected_end: date
    previous_start: date
    previous_end: date
    prior_start: date
    prior_end: date

    @property
    def partial(self) -> bool:
        return self.end < self.expected_end

    @property
    def elapsed_days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass(frozen=True)
class Observation:
    session_id: str
    local_date: date
    exercise_id: str
    exercise_name: str
    modality: str
    movement_pattern: str
    load_kg: float
    reps: int
    seconds: int
    assistance_kg: float
    rir: int | None
    rpe: float | None
    bodyweight_kg: float | None
    progression_multiplier: float


def _safe_timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _shift_month(day: date, delta: int) -> date:
    month_index = day.year * 12 + day.month - 1 + delta
    return date(month_index // 12, month_index % 12 + 1, 1)


def _month_end(start: date) -> date:
    return _shift_month(start, 1) - timedelta(days=1)


def resolve_period(period: str, timezone_name: str, through: date | None = None) -> PeriodWindow:
    if period not in SUPPORTED_PERIODS:
        raise ValueError(f"Unsupported strength period: {period}")
    today = datetime.now(_safe_timezone(timezone_name)).date()
    anchor = min(through or today, today)
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        expected_end = start + timedelta(days=6)
        previous_start = start - timedelta(days=7)
        prior_start = previous_start - timedelta(days=7)
        previous_expected_end = previous_start + timedelta(days=6)
        prior_expected_end = prior_start + timedelta(days=6)
    elif period == "month":
        start = anchor.replace(day=1)
        expected_end = _month_end(start)
        previous_start = _shift_month(start, -1)
        prior_start = _shift_month(start, -2)
        previous_expected_end = _month_end(previous_start)
        prior_expected_end = _month_end(prior_start)
    else:
        start = _shift_month(anchor.replace(day=1), -2)
        expected_end = _month_end(anchor.replace(day=1))
        previous_start = _shift_month(start, -3)
        prior_start = _shift_month(start, -6)
        previous_expected_end = start - timedelta(days=1)
        prior_expected_end = previous_start - timedelta(days=1)
    elapsed = (anchor - start).days
    previous_end = min(previous_start + timedelta(days=elapsed), previous_expected_end)
    prior_end = min(prior_start + timedelta(days=elapsed), prior_expected_end)
    return PeriodWindow(
        period_type=period,
        start=start,
        end=anchor,
        expected_end=expected_end,
        previous_start=previous_start,
        previous_end=previous_end,
        prior_start=prior_start,
        prior_end=prior_end,
    )


def estimated_one_rep_max(load_kg: float | None, reps: int | None, rir: int | None = None) -> float | None:
    if load_kg is None or load_kg <= 0 or reps is None or not 1 <= reps <= 12:
        return None
    effective_reps = reps + min(5, max(0, rir or 0))
    return round(load_kg * (1 + effective_reps / 30), 2)


def training_volume(load_kg: float | None, reps: int | None) -> float:
    if load_kg is None or load_kg <= 0 or reps is None or reps <= 0:
        return 0.0
    return round(load_kg * reps, 2)


def calisthenics_performance(
    *,
    reps: int | None,
    seconds: int | None,
    difficulty_multiplier: float,
    bodyweight_kg: float | None = None,
    added_load_kg: float | None = None,
    assistance_kg: float | None = None,
) -> float | None:
    repetition_signal = float(reps or 0)
    hold_signal = float(seconds or 0) / 5
    if repetition_signal <= 0 and hold_signal <= 0:
        return None
    resistance_signal = max(
        0.0,
        (bodyweight_kg or 0) * 0.12
        + (added_load_kg or 0) * 0.5
        - (assistance_kg or 0) * 0.25,
    )
    return round(
        difficulty_multiplier * (10 + repetition_signal + hold_signal + resistance_signal),
        2,
    )


def confidence_level(sessions: int, working_sets: float, exercise_diversity: int) -> str:
    if sessions < 3 and working_sets < 6:
        return "insufficient"
    if sessions >= 8 and working_sets >= 20 and exercise_diversity >= 2:
        return "high"
    if sessions >= 5 and working_sets >= 12 and exercise_diversity >= 2:
        return "medium"
    return "low"


def effort_quality(rirs: list[int], rpes: list[float]) -> float:
    if rirs:
        average = fmean(rirs)
        if 1 <= average <= 3:
            return 100.0
        if average < 1:
            return 84.0
        if average <= 4:
            return 72.0
        return 55.0
    if rpes:
        average = fmean(rpes)
        return round(max(45.0, min(100.0, 55 + average * 5)), 1)
    return 65.0


def muscle_strength_score(
    *,
    performance: float,
    trend_percent: float | None,
    weekly_sets: float,
    weekly_sessions: float,
    effort: float,
    exercise_diversity: int,
) -> float:
    diversity_factor = min(1.0, 0.75 + exercise_diversity * 0.125)
    performance_component = max(0.0, min(100.0, performance * diversity_factor))
    trend_component = 50.0 if trend_percent is None else max(0.0, min(100.0, 50 + trend_percent * 2))
    exposure_component = max(0.0, min(100.0, weekly_sets / 10 * 100))
    consistency_component = max(0.0, min(100.0, weekly_sessions / 2 * 100))
    return round(
        performance_component * 0.40
        + trend_component * 0.25
        + exposure_component * 0.15
        + consistency_component * 0.10
        + effort * 0.10,
        1,
    )


def classification(score: float | None, change_percent: float | None, confidence: str) -> str:
    if score is None or confidence == "insufficient":
        return "Insufficient Data"
    if confidence in {"medium", "high"} and change_percent is not None and change_percent >= 5:
        return "Improving"
    if score < 40:
        return "Needs Attention"
    if score < 55:
        return "Developing"
    if score < 70:
        return "Progressing"
    if score < 85:
        return "Strong"
    return "Very Strong"


def _utc_bounds(start: date, end: date, timezone_name: str) -> tuple[datetime, datetime]:
    local_timezone = _safe_timezone(timezone_name)
    start_dt = datetime.combine(start, time.min, tzinfo=local_timezone).astimezone(timezone.utc)
    end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=local_timezone).astimezone(timezone.utc)
    return start_dt, end_dt


def _local_date(value: datetime, timezone_name: str) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_safe_timezone(timezone_name)).date()


def _bodyweight_for(day: date, metrics: list[tuple[date, float]]) -> float | None:
    latest = None
    for metric_day, value in metrics:
        if metric_day > day:
            break
        latest = value
    return latest


def load_observations(
    db: Session,
    athlete_id: str,
    timezone_name: str,
    through: date,
) -> list[Observation]:
    _, end_dt = _utc_bounds(date(1970, 1, 1), through, timezone_name)
    metric_rows = db.scalars(
        select(BodyMetricEntry)
        .where(
            BodyMetricEntry.athlete_id == athlete_id,
            BodyMetricEntry.weight_kg.is_not(None),
            BodyMetricEntry.measured_at < end_dt,
        )
        .order_by(BodyMetricEntry.measured_at)
    ).all()
    metrics = [
        (_local_date(row.measured_at, timezone_name), float(row.weight_kg))
        for row in metric_rows
        if row.weight_kg is not None
    ]
    rows = db.execute(
        select(WorkoutSession, SetLog, Exercise, ExerciseProgression)
        .join(SetLog, SetLog.workout_session_id == WorkoutSession.id)
        .join(
            PrescribedExercise,
            PrescribedExercise.id == SetLog.prescribed_exercise_id,
        )
        .join(Exercise, Exercise.id == PrescribedExercise.exercise_id)
        .outerjoin(ExerciseProgression, ExerciseProgression.exercise_id == Exercise.id)
        .where(
            WorkoutSession.athlete_id == athlete_id,
            WorkoutSession.status == "completed",
            WorkoutSession.completed_at.is_not(None),
            WorkoutSession.completed_at < end_dt,
            SetLog.completed.is_(True),
        )
        .order_by(WorkoutSession.completed_at, SetLog.set_index)
    ).all()
    observations = []
    for session, set_log, exercise, progression in rows:
        completed_at = session.completed_at or session.started_at
        day = _local_date(completed_at, timezone_name)
        observations.append(
            Observation(
                session_id=session.id,
                local_date=day,
                exercise_id=exercise.id,
                exercise_name=exercise.name,
                modality=exercise.modality,
                movement_pattern=exercise.movement_pattern,
                load_kg=float(set_log.load_kg or 0),
                reps=int(set_log.reps or 0),
                seconds=int(set_log.seconds or 0),
                assistance_kg=float(set_log.assistance_kg or 0),
                rir=set_log.rir,
                rpe=set_log.rpe,
                bodyweight_kg=_bodyweight_for(day, metrics),
                progression_multiplier=(
                    float(progression.difficulty_multiplier) if progression else 1.0
                ),
            )
        )
    return observations


def _performance_value(observation: Observation) -> float | None:
    if observation.modality == "weighted_reps":
        return estimated_one_rep_max(observation.load_kg, observation.reps, observation.rir)
    if observation.modality in {"bodyweight_reps", "assisted_reps", "isometric_hold"}:
        return calisthenics_performance(
            reps=observation.reps,
            seconds=observation.seconds,
            difficulty_multiplier=observation.progression_multiplier,
            bodyweight_kg=observation.bodyweight_kg,
            added_load_kg=observation.load_kg,
            assistance_kg=observation.assistance_kg,
        )
    return None


def _percent_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _window_muscle_stats(
    observations: list[Observation],
    mappings: dict[str, list[tuple[MuscleGroup, float]]],
    start: date,
    end: date,
) -> dict[str, dict]:
    stats: dict[str, dict] = defaultdict(
        lambda: {
            "sets": 0.0,
            "sessions": set(),
            "volume": 0.0,
            "rirs": [],
            "rpes": [],
            "exercises": {},
        }
    )
    for observation in observations:
        if not start <= observation.local_date <= end:
            continue
        for group, contribution in mappings.get(observation.exercise_id, []):
            muscle = stats[group.slug]
            muscle["group"] = group
            muscle["sets"] += contribution
            muscle["sessions"].add(observation.session_id)
            muscle["volume"] += training_volume(observation.load_kg, observation.reps) * contribution
            if observation.rir is not None:
                muscle["rirs"].append(observation.rir)
            if observation.rpe is not None:
                muscle["rpes"].append(observation.rpe)
            exercise = muscle["exercises"].setdefault(
                observation.exercise_id,
                {
                    "id": observation.exercise_id,
                    "name": observation.exercise_name,
                    "contribution": contribution,
                    "sets": 0,
                    "volume": 0.0,
                    "best": None,
                    "best_e1rm": None,
                    "best_set": None,
                    "recent": [],
                },
            )
            exercise["sets"] += 1
            exercise["volume"] += training_volume(observation.load_kg, observation.reps)
            performance = _performance_value(observation)
            if performance is not None and (exercise["best"] is None or performance > exercise["best"]):
                exercise["best"] = performance
                exercise["best_set"] = {
                    "date": observation.local_date,
                    "load_kg": observation.load_kg or None,
                    "reps": observation.reps or None,
                    "seconds": observation.seconds or None,
                    "rir": observation.rir,
                    "performance": performance,
                }
            estimated = estimated_one_rep_max(
                observation.load_kg, observation.reps, observation.rir
            )
            if estimated is not None:
                exercise["best_e1rm"] = max(exercise["best_e1rm"] or 0, estimated)
            exercise["recent"].append(
                {
                    "date": observation.local_date,
                    "load_kg": observation.load_kg or None,
                    "reps": observation.reps or None,
                    "seconds": observation.seconds or None,
                    "rir": observation.rir,
                    "performance": performance,
                }
            )
    return stats


def _historical_bests(observations: list[Observation]) -> dict[str, float]:
    bests: dict[str, float] = {}
    for observation in observations:
        value = _performance_value(observation)
        if value is not None:
            bests[observation.exercise_id] = max(bests.get(observation.exercise_id, 0), value)
    return bests


def _trend_from_exercises(current: dict, previous: dict) -> float | None:
    changes = []
    weights = []
    for exercise_id, current_exercise in current.get("exercises", {}).items():
        previous_exercise = previous.get("exercises", {}).get(exercise_id)
        change = _percent_change(
            current_exercise.get("best"), previous_exercise.get("best") if previous_exercise else None
        )
        if change is not None:
            changes.append(change)
            weights.append(current_exercise["contribution"])
    if not changes:
        return None
    return round(sum(change * weight for change, weight in zip(changes, weights, strict=True)) / sum(weights), 1)


def _score_snapshot(
    stats: dict,
    previous_stats: dict,
    historical_bests: dict[str, float],
    elapsed_days: int,
) -> tuple[float | None, str, float | None]:
    sessions = len(stats.get("sessions", set()))
    working_sets = float(stats.get("sets", 0))
    exercises = stats.get("exercises", {})
    confidence = confidence_level(sessions, working_sets, len(exercises))
    trend = _trend_from_exercises(stats, previous_stats)
    if confidence == "insufficient":
        return None, confidence, trend
    ratios = []
    ratio_weights = []
    for exercise_id, exercise in exercises.items():
        current_best = exercise.get("best")
        historical_best = historical_bests.get(exercise_id)
        if current_best is not None and historical_best:
            ratios.append(min(100.0, current_best / historical_best * 100))
            ratio_weights.append(exercise["contribution"])
    performance = (
        sum(value * weight for value, weight in zip(ratios, ratio_weights, strict=True))
        / sum(ratio_weights)
        if ratios
        else 50.0
    )
    weeks = max(elapsed_days / 7, 1 / 7)
    score = muscle_strength_score(
        performance=performance,
        trend_percent=trend,
        weekly_sets=working_sets / weeks,
        weekly_sessions=sessions / weeks,
        effort=effort_quality(stats.get("rirs", []), stats.get("rpes", [])),
        exercise_diversity=len(exercises),
    )
    return score, confidence, trend


def _muscle_results(
    groups: list[MuscleGroup],
    current: dict[str, dict],
    previous: dict[str, dict],
    prior: dict[str, dict],
    historical_bests: dict[str, float],
    elapsed_days: int,
) -> list[dict]:
    results = []
    for group in groups:
        current_stats = current.get(group.slug, {})
        previous_stats = previous.get(group.slug, {})
        prior_stats = prior.get(group.slug, {})
        score, confidence, trend = _score_snapshot(
            current_stats, previous_stats, historical_bests, elapsed_days
        )
        previous_score, _, _ = _score_snapshot(
            previous_stats, prior_stats, historical_bests, elapsed_days
        )
        change = _percent_change(score, previous_score)
        exercises = sorted(
            current_stats.get("exercises", {}).values(),
            key=lambda item: (item["sets"], item["best"] or 0),
            reverse=True,
        )
        for exercise in exercises:
            exercise["volume"] = round(exercise["volume"], 1)
            exercise["recent"] = sorted(
                exercise["recent"], key=lambda item: item["date"], reverse=True
            )[:8]
            previous_exercise = previous_stats.get("exercises", {}).get(exercise["id"])
            exercise["previous_best"] = (
                previous_exercise.get("best") if previous_exercise else None
            )
            exercise["change_percent"] = _percent_change(
                exercise.get("best"), exercise["previous_best"]
            )
        results.append(
            {
                "id": group.id,
                "slug": group.slug,
                "name": group.name,
                "body_region": group.body_region,
                "score": score,
                "previous_score": previous_score,
                "change_percent": change,
                "performance_change_percent": trend,
                "status": classification(score, change, confidence),
                "confidence": confidence,
                "sessions": len(current_stats.get("sessions", set())),
                "working_sets": round(current_stats.get("sets", 0), 1),
                "training_volume_kg": round(current_stats.get("volume", 0), 1),
                "exercise_diversity": len(exercises),
                "top_exercise": exercises[0] if exercises else None,
                "exercises": exercises,
            }
        )
    return results


BALANCE_GROUPS = (
    ("Push vs Pull", ["chest", "upper-chest", "front-delts", "side-delts", "triceps"], ["lats", "upper-back", "traps", "rear-delts", "biceps"]),
    ("Chest vs Back", ["chest", "upper-chest"], ["lats", "upper-back"]),
    ("Quadriceps vs Hamstrings", ["quadriceps"], ["hamstrings"]),
    ("Biceps vs Triceps", ["biceps"], ["triceps"]),
    ("Upper vs Lower Body", ["chest", "upper-chest", "lats", "upper-back", "traps", "front-delts", "side-delts", "rear-delts", "biceps", "triceps", "forearms"], ["glutes", "quadriceps", "hamstrings", "calves", "adductors", "hip-flexors"]),
)


def _side_summary(muscles_by_slug: dict[str, dict], slugs: list[str]) -> dict:
    rows = [muscles_by_slug[slug] for slug in slugs if slug in muscles_by_slug]
    scored = [row for row in rows if row["score"] is not None]
    return {
        "score": round(fmean(row["score"] for row in scored), 1) if scored else None,
        "working_sets": round(sum(row["working_sets"] for row in rows), 1),
        "sessions": max((row["sessions"] for row in rows), default=0),
        "confidence": "insufficient" if not scored else min(
            (row["confidence"] for row in scored),
            key=lambda value: {"insufficient": 0, "low": 1, "medium": 2, "high": 3}[value],
        ),
    }


def balance_analysis(muscles: list[dict]) -> list[dict]:
    muscles_by_slug = {muscle["slug"]: muscle for muscle in muscles}
    output = []
    for name, left_slugs, right_slugs in BALANCE_GROUPS:
        left = _side_summary(muscles_by_slug, left_slugs)
        right = _side_summary(muscles_by_slug, right_slugs)
        difference = _percent_change(left["score"], right["score"])
        if left["score"] is None or right["score"] is None:
            insight = "More completed training history is needed for this performance comparison."
        else:
            left_name, right_name = name.split(" vs ")
            if abs(difference or 0) < 10:
                insight = f"Recorded {left_name.lower()} and {right_name.lower()} performance is currently similar."
            else:
                leader = left_name if (difference or 0) > 0 else right_name
                insight = f"Recorded performance currently trends toward {leader.lower()} by {abs(difference or 0):.1f}%."
            if name == "Quadriceps vs Hamstrings" and right["working_sets"] < left["working_sets"] * 0.6:
                insight = "Hamstring training exposure and relative performance are currently lower than quadriceps."
        output.append(
            {
                "name": name,
                "left_label": name.split(" vs ")[0],
                "right_label": name.split(" vs ")[1],
                "left": left,
                "right": right,
                "difference_percent": difference,
                "insight": insight,
            }
        )
    return output


def deterministic_recommendations(muscles: list[dict]) -> list[dict]:
    recommendations = []
    sufficient = [muscle for muscle in muscles if muscle["score"] is not None]
    for muscle in sufficient:
        if muscle["change_percent"] is not None and muscle["change_percent"] >= 8 and muscle["confidence"] in {"medium", "high"}:
            recommendations.append(
                {
                    "muscle": muscle["name"],
                    "action": "Maintain current progression",
                    "reason": f"{muscle['name']} was one of your fastest improving areas this period, increasing {muscle['change_percent']:.1f}%.",
                    "confidence": muscle["confidence"],
                }
            )
        elif muscle["working_sets"] < 6 and muscle["status"] in {"Needs Attention", "Developing"}:
            recommendations.append(
                {
                    "muscle": muscle["name"],
                    "action": "Build consistent exposure",
                    "reason": f"Only {muscle['working_sets']:g} contribution-weighted sets were recorded for {muscle['name']} in this period.",
                    "confidence": muscle["confidence"],
                }
            )
    if not sufficient:
        recommendations.append(
            {
                "muscle": None,
                "action": "Keep building your strength profile",
                "reason": "Complete at least three relevant sessions or six meaningful working sets before AthleteOS classifies an area.",
                "confidence": "insufficient",
            }
        )
    return recommendations[:5]


def _overall(muscles: list[dict]) -> dict:
    sufficient = [muscle for muscle in muscles if muscle["score"] is not None]
    if not sufficient:
        return {
            "score": None,
            "previous_score": None,
            "change_percent": None,
            "confidence": "insufficient",
        }
    weights = [max(1.0, muscle["working_sets"]) for muscle in sufficient]
    score = round(
        sum(muscle["score"] * weight for muscle, weight in zip(sufficient, weights, strict=True))
        / sum(weights),
        1,
    )
    previous_rows = [muscle for muscle in sufficient if muscle["previous_score"] is not None]
    previous_score = (
        round(fmean(muscle["previous_score"] for muscle in previous_rows), 1)
        if previous_rows
        else None
    )
    confidence = max(
        (muscle["confidence"] for muscle in sufficient),
        key=lambda value: {"insufficient": 0, "low": 1, "medium": 2, "high": 3}[value],
    )
    return {
        "score": score,
        "previous_score": previous_score,
        "change_percent": _percent_change(score, previous_score),
        "confidence": confidence,
    }


def _trend_points(
    window: PeriodWindow,
    observations: list[Observation],
    mappings: dict[str, list[tuple[MuscleGroup, float]]],
    groups: list[MuscleGroup],
    historical_bests: dict[str, float],
) -> list[dict]:
    step = 1 if window.period_type == "week" else 7 if window.period_type == "month" else 14
    points = []
    cursor = window.start
    while cursor <= window.end:
        point_end = min(cursor + timedelta(days=step - 1), window.end)
        elapsed = (point_end - window.start).days
        previous_end = min(window.previous_start + timedelta(days=elapsed), window.previous_end)
        prior_end = min(window.prior_start + timedelta(days=elapsed), window.prior_end)
        current_stats = _window_muscle_stats(observations, mappings, window.start, point_end)
        previous_stats = _window_muscle_stats(
            observations, mappings, window.previous_start, previous_end
        )
        prior_stats = _window_muscle_stats(observations, mappings, window.prior_start, prior_end)
        muscles = _muscle_results(
            groups,
            current_stats,
            previous_stats,
            prior_stats,
            historical_bests,
            elapsed + 1,
        )
        point = {"date": point_end, "overall": _overall(muscles)["score"]}
        point.update({muscle["slug"]: muscle["score"] for muscle in muscles})
        points.append(point)
        cursor = point_end + timedelta(days=1)
    return points


def build_strength_analysis(
    db: Session,
    *,
    athlete_id: str,
    timezone_name: str,
    period: str,
    through: date | None = None,
) -> dict:
    window = resolve_period(period, timezone_name, through)
    groups = db.scalars(select(MuscleGroup).order_by(MuscleGroup.sort_order)).all()
    mapping_rows = db.execute(
        select(ExerciseMuscleMapping, MuscleGroup).join(
            MuscleGroup, MuscleGroup.id == ExerciseMuscleMapping.muscle_group_id
        )
    ).all()
    mappings: dict[str, list[tuple[MuscleGroup, float]]] = defaultdict(list)
    for mapping, group in mapping_rows:
        mappings[mapping.exercise_id].append((group, mapping.contribution_weight))
    observations = load_observations(db, athlete_id, timezone_name, window.end)
    current = _window_muscle_stats(observations, mappings, window.start, window.end)
    previous = _window_muscle_stats(
        observations, mappings, window.previous_start, window.previous_end
    )
    prior = _window_muscle_stats(observations, mappings, window.prior_start, window.prior_end)
    bests = _historical_bests(observations)
    muscles = _muscle_results(
        groups, current, previous, prior, bests, window.elapsed_days
    )
    overall = _overall(muscles)
    sufficient = [muscle for muscle in muscles if muscle["score"] is not None]
    strongest = max(sufficient, key=lambda row: row["score"], default=None)
    improved = max(
        (muscle for muscle in sufficient if muscle["change_percent"] is not None),
        key=lambda row: row["change_percent"],
        default=None,
    )
    attention = min(
        (muscle for muscle in sufficient if muscle["score"] < 70),
        key=lambda row: row["score"],
        default=None,
    )
    completed_sessions = {
        observation.session_id
        for observation in observations
        if window.start <= observation.local_date <= window.end
    }
    return {
        "analytics_version": ANALYTICS_VERSION,
        "period": {
            "type": period,
            "start": window.start,
            "end": window.end,
            "expected_end": window.expected_end,
            "partial": window.partial,
            "comparison_start": window.previous_start,
            "comparison_end": window.previous_end,
            "timezone": timezone_name,
        },
        "profile_state": (
            "ready" if sufficient else "building" if completed_sessions else "empty"
        ),
        "sessions_recorded": len(completed_sessions),
        "unlock_target_sessions": 3,
        "overall": overall,
        "strongest": (
            {"muscle_id": strongest["id"], "muscle": strongest["name"], "score": strongest["score"]}
            if strongest
            else None
        ),
        "most_improved": (
            {
                "muscle_id": improved["id"],
                "muscle": improved["name"],
                "change_percent": improved["change_percent"],
            }
            if improved and improved["change_percent"] > 0
            else None
        ),
        "needs_attention": (
            {"muscle_id": attention["id"], "muscle": attention["name"], "score": attention["score"]}
            if attention
            else None
        ),
        "muscles": muscles,
        "balance": balance_analysis(muscles),
        "trend": _trend_points(window, observations, mappings, groups, bests),
        "recommendations": deterministic_recommendations(muscles),
        "methodology_note": "Scores describe user-relative recorded training performance and exposure, not isolated biological or medical strength.",
    }

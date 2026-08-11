from datetime import date, datetime, timezone

import pytest
from conftest import complete_onboarding, register
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.domains.strength import (
    balance_analysis,
    calisthenics_performance,
    confidence_level,
    deterministic_recommendations,
    estimated_one_rep_max,
    muscle_strength_score,
    resolve_period,
    training_volume,
)
from app.domains.strength_catalog import exercise_contributions
from app.models import (
    AthleteProfile,
    Exercise,
    ExerciseMuscleMapping,
    PrescribedExercise,
    Program,
    ProgramDay,
    SetLog,
    StrengthReport,
    User,
    WorkoutSession,
    new_id,
)


def test_epley_rep_eligibility_and_rir_adjustment():
    assert estimated_one_rep_max(60, 10) == 80
    assert estimated_one_rep_max(60, 10, 3) == 86
    assert estimated_one_rep_max(60, 13) is None
    assert estimated_one_rep_max(0, 8) is None
    assert estimated_one_rep_max(60, 0) is None


def test_volume_and_calisthenics_are_separate_performance_signals():
    assert training_volume(60, 10) == 600
    assert training_volume(None, 10) == 0
    pull_up = calisthenics_performance(
        reps=10,
        seconds=None,
        difficulty_multiplier=1.8,
        bodyweight_kg=75,
        added_load_kg=0,
        assistance_kg=0,
    )
    assisted = calisthenics_performance(
        reps=10,
        seconds=None,
        difficulty_multiplier=1.0,
        bodyweight_kg=75,
        added_load_kg=0,
        assistance_kg=20,
    )
    assert pull_up is not None and assisted is not None and pull_up > assisted


def test_primary_and_secondary_muscles_keep_different_contribution_weights():
    exercise = Exercise(
        name="Bench Press",
        slug="bench-press-test",
        category="Chest",
        primary_muscles=["Chest"],
        secondary_muscles=["Triceps", "Front Delts"],
        movement_pattern="horizontal_push",
    )
    mappings = {slug: (role, weight) for slug, role, weight in exercise_contributions(exercise)}
    assert mappings["chest"] == ("PRIMARY", 1.0)
    assert mappings["triceps"] == ("SECONDARY", 0.35)
    assert mappings["front-delts"] == ("SECONDARY", 0.35)


def test_strength_score_and_confidence_are_bounded_and_data_gated():
    assert confidence_level(1, 5, 1) == "insufficient"
    assert confidence_level(3, 6, 1) == "low"
    assert confidence_level(5, 12, 2) == "medium"
    assert confidence_level(8, 20, 2) == "high"
    score = muscle_strength_score(
        performance=100,
        trend_percent=5,
        weekly_sets=10,
        weekly_sessions=2,
        effort=100,
        exercise_diversity=2,
    )
    assert score == 90
    assert 0 <= muscle_strength_score(
        performance=500,
        trend_percent=500,
        weekly_sets=500,
        weekly_sessions=50,
        effort=100,
        exercise_diversity=5,
    ) <= 100


def test_calendar_periods_use_equivalent_partial_windows_and_user_timezone():
    week = resolve_period("week", "Asia/Kolkata", date(2026, 8, 12))
    assert (week.start, week.end) == (date(2026, 8, 10), date(2026, 8, 12))
    assert (week.previous_start, week.previous_end) == (
        date(2026, 8, 3),
        date(2026, 8, 5),
    )
    month = resolve_period("month", "Asia/Kolkata", date(2026, 8, 12))
    assert month.partial is True
    assert (month.previous_start, month.previous_end) == (
        date(2026, 7, 1),
        date(2026, 7, 12),
    )


def test_balance_and_report_rules_use_performance_language():
    muscles = [
        {
            "slug": "quadriceps",
            "name": "Quadriceps",
            "score": 76.0,
            "working_sets": 14.0,
            "sessions": 3,
            "confidence": "medium",
            "change_percent": 2.0,
            "status": "Strong",
        },
        {
            "slug": "hamstrings",
            "name": "Hamstrings",
            "score": 50.0,
            "working_sets": 5.0,
            "sessions": 2,
            "confidence": "low",
            "change_percent": 1.0,
            "status": "Developing",
        },
        {
            "slug": "chest",
            "name": "Chest",
            "score": 80.0,
            "working_sets": 12.0,
            "sessions": 5,
            "confidence": "medium",
            "change_percent": 9.0,
            "status": "Improving",
        },
    ]
    quad_balance = next(
        row for row in balance_analysis(muscles) if row["name"] == "Quadriceps vs Hamstrings"
    )
    assert "training exposure" in quad_balance["insight"]
    assert "biologically" not in quad_balance["insight"]
    recommendation = next(
        row for row in deterministic_recommendations(muscles) if row["muscle"] == "Chest"
    )
    assert recommendation["muscle"] == "Chest"
    assert "increasing 9.0%" in recommendation["reason"]


def _seed_two_week_history(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
        exercises = {
            exercise.slug: exercise
            for exercise in db.scalars(
                select(Exercise).where(
                    Exercise.slug.in_(
                        ["barbell-bench-press", "lat-pulldown", "back-squat", "romanian-deadlift"]
                    )
                )
            ).all()
        }
        program = Program(
            id=new_id(),
            athlete_id=profile.id,
            name="Strength Intelligence Test",
            status="inactive",
            starts_on=date(2026, 7, 27),
        )
        day = ProgramDay(
            id=new_id(),
            program_id=program.id,
            day_index=1,
            title="Full Body Test",
            focus=["Chest", "Back", "Legs"],
            scheduled_date=date(2026, 7, 29),
            estimated_minutes=60,
        )
        db.add_all([program, day])
        db.flush()
        prescriptions = {}
        for index, slug in enumerate(exercises, 1):
            prescription = PrescribedExercise(
                id=new_id(),
                program_day_id=day.id,
                exercise_id=exercises[slug].id,
                order_index=index,
                target_sets=3,
                rep_min=5,
                rep_max=12,
                rest_seconds=120,
                target_rir=2,
            )
            prescriptions[slug] = prescription
            db.add(prescription)
        db.flush()
        histories = [
            (
                date(2026, 7, 29),
                {
                    "barbell-bench-press": [(60, 8), (60, 8), (60, 7)],
                    "lat-pulldown": [(55, 10), (55, 10), (55, 9)],
                    "back-squat": [(80, 8), (80, 8), (80, 8)],
                    "romanian-deadlift": [(60, 10), (60, 10)],
                },
            ),
            (
                date(2026, 8, 5),
                {
                    "barbell-bench-press": [(62.5, 9), (62.5, 8), (62.5, 8)],
                    "lat-pulldown": [(60, 10), (60, 10), (60, 9)],
                    "back-squat": [(82.5, 8), (82.5, 8), (82.5, 8)],
                    "romanian-deadlift": [(60, 10), (60, 9)],
                },
            ),
        ]
        for session_day, exercises_and_sets in histories:
            completed_at = datetime(
                session_day.year, session_day.month, session_day.day, 12, tzinfo=timezone.utc
            )
            session = WorkoutSession(
                id=new_id(),
                athlete_id=profile.id,
                program_day_id=day.id,
                status="completed",
                started_at=completed_at,
                completed_at=completed_at,
                total_volume_kg=0,
            )
            db.add(session)
            for slug, sets in exercises_and_sets.items():
                for set_index, (load, reps) in enumerate(sets, 1):
                    db.add(
                        SetLog(
                            id=new_id(),
                            workout_session_id=session.id,
                            prescribed_exercise_id=prescriptions[slug].id,
                            set_index=set_index,
                            client_operation_id=new_id(),
                            load_kg=load,
                            reps=reps,
                            rir=2,
                            completed=True,
                        )
                    )
        db.commit()


def test_real_workout_history_drives_strength_progress_and_report(client: TestClient):
    register(client, "strength@example.com")
    complete_onboarding(client)
    _seed_two_week_history("strength@example.com")

    response = client.get(
        "/api/v1/progress/strength",
        params={"period": "week", "through": "2026-08-09"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    muscles = {muscle["slug"]: muscle for muscle in payload["muscles"]}
    assert muscles["chest"]["performance_change_percent"] > 0
    assert muscles["lats"]["performance_change_percent"] > 0
    assert muscles["quadriceps"]["performance_change_percent"] > 0
    assert muscles["hamstrings"]["working_sets"] < muscles["quadriceps"]["working_sets"]
    assert payload["period"]["comparison_start"] == "2026-07-27"
    assert payload["methodology_note"].startswith("Scores describe user-relative")

    generated = client.post(
        "/api/v1/progress/strength-report",
        json={"period": "3_months", "through": "2026-08-09"},
    )
    assert generated.status_code == 201, generated.text
    report = generated.json()
    assert report["analytics_version"] == "strength_v1"
    assert report["report"]["training_summary"]["sessions"] == 2
    assert report["report"]["training_summary"]["working_sets"] == 22
    assert report["report"]["analysis"]["overall"]["score"] is not None
    assert client.get("/api/v1/progress/strength-reports").json()["items"][0]["id"] == report["id"]


def test_strength_report_authorization_and_full_dataset_mapping(client: TestClient):
    register(client, "owner@example.com")
    complete_onboarding(client)
    report = client.post(
        "/api/v1/progress/strength-report",
        json={"period": "month", "through": "2026-08-12"},
    )
    assert report.status_code == 201
    report_id = report.json()["id"]

    with SessionLocal() as db:
        published = db.scalar(
            select(func.count()).select_from(Exercise).where(Exercise.published.is_(True))
        )
        mapped_exercises = db.scalar(
            select(func.count(func.distinct(ExerciseMuscleMapping.exercise_id)))
        )
        mapping_count = db.scalar(select(func.count()).select_from(ExerciseMuscleMapping))
        assert published == 151
        assert mapped_exercises == published
        assert mapping_count >= published
        assert db.scalar(select(func.count()).select_from(StrengthReport)) == 1

    assert client.post("/api/v1/auth/logout").status_code == 204
    register(client, "other@example.com")
    denied = client.get(f"/api/v1/progress/strength-reports/{report_id}")
    assert denied.status_code == 404
    assert denied.json()["code"] == "STRENGTH_REPORT_NOT_FOUND"


def test_unsupported_period_is_rejected():
    with pytest.raises(ValueError, match="Unsupported strength period"):
        resolve_period("year", "UTC")

from datetime import date

from app.domains.habits import calculate_streak
from app.domains.readiness import calculate_readiness
from app.models import Habit, HabitCompletion


def test_schedule_aware_streak_ignores_unscheduled_days():
    habit = Habit(
        id="habit",
        athlete_id="athlete",
        name="Train MWF",
        schedule={"frequency": "selected_weekdays", "weekdays": [0, 2, 4]},
    )
    completions = [
        HabitCompletion(habit_id="habit", athlete_id="athlete", local_date=date(2026, 8, 3), completed=True, value=1),
        HabitCompletion(habit_id="habit", athlete_id="athlete", local_date=date(2026, 8, 5), completed=True, value=1),
        HabitCompletion(habit_id="habit", athlete_id="athlete", local_date=date(2026, 8, 7), completed=True, value=1),
        HabitCompletion(habit_id="habit", athlete_id="athlete", local_date=date(2026, 8, 10), completed=True, value=1),
    ]
    streak = calculate_streak(habit, completions, date(2026, 8, 11))
    assert streak == {"current": 4, "best": 4}


def test_readiness_is_explainable_and_bounded():
    poor_score, poor_reasons = calculate_readiness({"sleep_hours": 4.5, "energy": 1, "soreness": 5, "stress": 5})
    good_score, good_reasons = calculate_readiness({"sleep_hours": 8, "energy": 5, "soreness": 1, "stress": 1})
    assert 20 <= poor_score < good_score <= 100
    assert poor_reasons
    assert good_reasons


import calendar
from datetime import date, timedelta

from app.models import Habit, HabitCompletion


def is_scheduled(habit: Habit, day: date) -> bool:
    frequency = habit.schedule.get("frequency", "daily")
    if frequency == "selected_weekdays":
        return day.weekday() in habit.schedule.get("weekdays", [])
    return True


def calculate_streak(habit: Habit, completions: list[HabitCompletion], through: date) -> dict:
    target = habit.target_value or 1
    completed = {
        item.local_date for item in completions if item.completed and item.value >= target
    }
    cursor = through
    current = 0
    while True:
        if not is_scheduled(habit, cursor):
            cursor -= timedelta(days=1)
            continue
        if cursor in completed:
            current += 1
            cursor -= timedelta(days=1)
            continue
        if cursor == through:
            cursor -= timedelta(days=1)
            continue
        break
    ordered = sorted(completed)
    best = run = 0
    previous = None
    for day in ordered:
        if not is_scheduled(habit, day):
            continue
        if previous is None:
            run = 1
        else:
            cursor = previous + timedelta(days=1)
            while cursor < day and not is_scheduled(habit, cursor):
                cursor += timedelta(days=1)
            run = run + 1 if cursor == day else 1
        best = max(best, run)
        previous = day
    return {"current": current, "best": best}


def month_dates(month: str) -> list[date]:
    year, month_number = (int(part) for part in month.split("-", 1))
    _, count = calendar.monthrange(year, month_number)
    return [date(year, month_number, day) for day in range(1, count + 1)]

from conftest import complete_onboarding, register
from fastapi.testclient import TestClient


def test_progress_habit_rates_match_scheduled_elapsed_tracker_days(client: TestClient):
    register(client)
    complete_onboarding(client)
    habits = client.get("/api/v1/habits").json()["items"]
    sleep = next(item for item in habits if item["name"] == "Sleep 7+ hours")
    mobility = next(item for item in habits if item["name"] == "Mobility 10 minutes")

    selected = client.post(
        "/api/v1/habits",
        json={
            "name": "Selected-day recovery",
            "category": "recovery",
            "measurement_type": "boolean",
            "target_value": 1,
            "schedule": {"frequency": "selected_weekdays", "weekdays": [0, 2]},
        },
    ).json()["habit"]

    for habit_id, local_day in [
        (sleep["id"], "2026-08-10"),
        (sleep["id"], "2026-08-11"),
        (sleep["id"], "2026-08-12"),
        (mobility["id"], "2026-08-10"),
        (mobility["id"], "2026-08-11"),
        (selected["id"], "2026-08-10"),
        (selected["id"], "2026-08-12"),
        # This completion is on an unscheduled Tuesday and must not inflate adherence.
        (selected["id"], "2026-08-11"),
        # This completion is after the athlete-local reporting date and must be excluded.
        (sleep["id"], "2026-08-13"),
    ]:
        response = client.put(
            f"/api/v1/habits/{habit_id}/days/{local_day}",
            json={"value": 1, "completed": True},
        )
        assert response.status_code == 200

    weekly = client.get(
        "/api/v1/reports/weekly",
        params={"week_of": "2026-08-12", "through": "2026-08-12"},
    ).json()
    assert weekly["habits"] == {"completions": 7, "completion_rate": 50.0}

    monthly = client.get(
        "/api/v1/reports/monthly",
        params={"month": "2026-08", "through": "2026-08-12"},
    ).json()
    assert monthly["habits"] == {"completions": 7, "completion_rate": 13.5}

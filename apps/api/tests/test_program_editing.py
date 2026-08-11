from conftest import complete_onboarding, register
from fastapi.testclient import TestClient


def test_athlete_can_change_and_customize_plan_without_rewriting_history(client: TestClient):
    register(client)
    complete_onboarding(client)

    original = client.get("/api/v1/programs/active").json()["program"]
    original_day = original["days"][0]
    session_response = client.post(
        "/api/v1/workouts", json={"program_day_id": original_day["id"]}
    )
    assert session_response.status_code == 201
    historical_session_id = session_response.json()["session_id"]

    templates = client.get("/api/v1/programs/templates")
    assert templates.status_code == 200
    assert templates.json()["total"] == 30
    assert any(item["recommended"] for item in templates.json()["items"])

    activated = client.post("/api/v1/programs/templates/SPLIT001/activate")
    assert activated.status_code == 201
    template_program = activated.json()["program"]
    assert template_program["id"] != original["id"]
    assert template_program["name"] == "Full Body 2-Day"
    assert len(template_program["days"]) == 2

    historical_session = client.get(f"/api/v1/workouts/{historical_session_id}")
    assert historical_session.status_code == 200
    assert historical_session.json()["session"]["day"]["id"] == original_day["id"]

    added_day = client.post(
        f"/api/v1/programs/{template_program['id']}/days",
        json={"title": "Grip and Mobility", "focus": ["Grip", "Mobility"], "estimated_minutes": 35},
    )
    assert added_day.status_code == 201
    custom_program_id = added_day.json()["program_id"]
    custom_day_id = added_day.json()["day_id"]

    exercise_results = client.get("/api/v1/exercises?q=farmer%20carry&page_size=1").json()
    exercise_id = exercise_results["items"][0]["id"]
    added_exercise = client.post(
        f"/api/v1/programs/{custom_program_id}/days/{custom_day_id}/exercises",
        json={
            "exercise_id": exercise_id,
            "target_sets": 4,
            "rep_min": 20,
            "rep_max": 40,
            "rest_seconds": 90,
            "target_rir": 2,
        },
    )
    assert added_exercise.status_code == 201

    active = client.get("/api/v1/programs/active").json()["program"]
    custom_day = next(day for day in active["days"] if day["id"] == added_exercise.json()["day_id"])
    assert custom_day["title"] == "Grip and Mobility"
    assert custom_day["exercises"][0]["exercise"]["name"] == "Farmer Carry"
    assert custom_day["exercises"][0]["target_sets"] == 4

    removed = client.delete(
        f"/api/v1/programs/{active['id']}/days/{custom_day['id']}"
    )
    assert removed.status_code == 204
    final_program = client.get("/api/v1/programs/active").json()["program"]
    assert len(final_program["days"]) == 2
    assert all(day["title"] != "Grip and Mobility" for day in final_program["days"])


def test_plan_editor_validates_ownership_duplicates_and_minimums(client: TestClient):
    register(client)
    complete_onboarding(client)
    program = client.get("/api/v1/programs/active").json()["program"]
    day = program["days"][0]
    first = day["exercises"][0]

    duplicate = client.post(
        f"/api/v1/programs/{program['id']}/days/{day['id']}/exercises",
        json={"exercise_id": first["exercise"]["id"]},
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["code"] == "EXERCISE_ALREADY_PLANNED"

    invalid_range = client.patch(
        f"/api/v1/programs/{program['id']}/days/{day['id']}/exercises/{first['id']}",
        json={"exercise_id": first["exercise"]["id"], "rep_min": 12, "rep_max": 8},
    )
    assert invalid_range.status_code == 400
    assert invalid_range.json()["code"] == "INVALID_REP_RANGE"


def test_athlete_can_reschedule_a_program_day_without_rewriting_the_old_version(
    client: TestClient,
):
    register(client)
    complete_onboarding(client)
    program = client.get("/api/v1/programs/active").json()["program"]
    day = program["days"][0]

    rescheduled = client.patch(
        f"/api/v1/programs/{program['id']}/days/{day['id']}",
        json={
            "title": day["title"],
            "focus": day["focus"],
            "scheduled_date": "2030-02-14",
            "estimated_minutes": day["estimated_minutes"],
        },
    )

    assert rescheduled.status_code == 200
    active = client.get("/api/v1/programs/active").json()["program"]
    assert active["id"] != program["id"]
    assert active["days"][0]["scheduled_date"] == "2030-02-14"
    assert active["rationale"][-1] == f"Customized: updated {day['title']}"

from datetime import date
from uuid import uuid4

from conftest import complete_onboarding, register
from fastapi.testclient import TestClient


def test_exact_mvp_flow_persists_across_login(client: TestClient):
    register(client)
    complete_onboarding(client)

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["onboarding_completed"] is True
    assert me.json()["user"]["experience_level"] == "intermediate"

    program_response = client.get("/api/v1/programs/active")
    assert program_response.status_code == 200
    program = program_response.json()["program"]
    assert len(program["days"]) == 5
    assert "Bodybuilding" in program["name"]
    push_day = program["days"][0]
    assert push_day["title"] == "Push Day"
    assert len(push_day["exercises"]) >= 4

    start = client.post("/api/v1/workouts", json={"program_day_id": push_day["id"]})
    assert start.status_code == 201
    session_id = start.json()["session_id"]
    prescription = push_day["exercises"][0]
    for set_index in range(1, prescription["target_sets"] + 1):
        operation_id = str(uuid4())
        payload = {
            "prescribed_exercise_id": prescription["id"],
            "set_index": set_index,
            "client_operation_id": operation_id,
            "load_kg": 60,
            "reps": prescription["rep_max"],
            "rir": 2,
            "completed": True,
        }
        logged = client.post(f"/api/v1/workouts/{session_id}/sets", json=payload)
        assert logged.status_code == 201, logged.text
        if set_index == 1:
            replay = client.post(f"/api/v1/workouts/{session_id}/sets", json=payload)
            assert replay.status_code == 201
            assert replay.json()["idempotent_replay"] is True

    completed = client.post(
        f"/api/v1/workouts/{session_id}/complete",
        json={"session_rpe": 8, "rating": "good", "notes": "Strong session"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["summary"]["sets_completed"] == prescription["target_sets"]
    assert completed.json()["summary"]["total_volume_kg"] > 0

    food_search = client.get("/api/v1/foods/search", params={"q": "alu mutter"})
    assert food_search.status_code == 200
    food = food_search.json()["items"][0]
    assert food["canonical_name"] == "Aloo Matar Sabzi"
    assert food["data_quality"] == "estimated"
    serving = food["servings"][0]
    today = date.today().isoformat()
    meal = client.post(
        f"/api/v1/meals/{today}/lunch/items",
        json={"food_id": food["id"], "serving_id": serving["id"], "quantity": 1},
    )
    assert meal.status_code == 201, meal.text

    water_operation = str(uuid4())
    water = client.post(
        "/api/v1/water",
        json={"amount_ml": 500, "local_date": today, "client_operation_id": water_operation},
    )
    assert water.status_code == 201
    replay = client.post(
        "/api/v1/water",
        json={"amount_ml": 500, "local_date": today, "client_operation_id": water_operation},
    )
    assert replay.json()["idempotent_replay"] is True

    habits = client.get("/api/v1/habits").json()["items"]
    manual_habit = next(habit for habit in habits if not habit["derived_source"])
    tick = client.put(
        f"/api/v1/habits/{manual_habit['id']}/days/{today}",
        json={"value": 1, "completed": True},
    )
    assert tick.status_code == 200

    dashboard = client.get("/api/v1/dashboard/today", params={"local_date": today})
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["metrics"]["weight_kg"] == 72.5
    assert dashboard.json()["nutrition"]["totals"]["energy_kcal"] > 0

    report = client.get("/api/v1/reports/weekly", params={"week_of": today})
    assert report.status_code == 200
    assert report.json()["training"]["sessions_completed"] == 1

    assert client.post("/api/v1/auth/logout").status_code == 204
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "athlete@example.com", "password": "StrongPass123"},
    )
    assert login.status_code == 200
    history = client.get("/api/v1/workouts")
    assert history.status_code == 200
    assert history.json()["items"][0]["status"] == "completed"
    nutrition = client.get(f"/api/v1/nutrition/days/{today}")
    assert nutrition.json()["meals"][0]["items"][0]["name"] == "Aloo Matar Sabzi"


def test_login_uses_the_same_canonical_email_as_registration(client: TestClient):
    register(client, "Athlete.MixedCase@example.com")
    assert client.post("/api/v1/auth/logout").status_code == 204

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "athlete.mixedcase@EXAMPLE.COM", "password": "StrongPass123"},
    )

    assert login.status_code == 200
    assert login.json()["user"]["email"] == "athlete.mixedcase@example.com"
    assert client.get("/api/v1/auth/me").status_code == 200


def test_cross_user_workout_access_is_denied(client: TestClient):
    register(client, "first@example.com")
    complete_onboarding(client)
    day_id = client.get("/api/v1/programs/active").json()["program"]["days"][0]["id"]
    session_id = client.post("/api/v1/workouts", json={"program_day_id": day_id}).json()["session_id"]
    client.post("/api/v1/auth/logout")

    register(client, "second@example.com")
    response = client.get(f"/api/v1/workouts/{session_id}")
    assert response.status_code == 404
    assert response.json()["code"] == "WORKOUT_NOT_FOUND"


def test_bodyweight_only_plan_excludes_machine_exercises(client: TestClient):
    register(client)
    steps = [
        (1, {"height_cm": 170, "weight_kg": 65, "unit_system": "metric"}),
        (2, {"water_target_ml": 2500, "sleep_hours": 7, "activity_level": "lightly_active"}),
        (3, {"experience_level": "beginner"}),
        (4, {"training_type": "calisthenics"}),
        (5, {"primary_goal": "skill_development"}),
        (6, {"equipment": ["bodyweight"]}),
        (7, {"days_per_week": 3, "preferred_weekdays": [], "session_minutes": 45}),
        (8, {}),
        (9, {"skip_scan": True}),
    ]
    for step, data in steps:
        assert client.put("/api/v1/onboarding", json={"step": step, "data": data}).status_code == 200
    program = client.get("/api/v1/programs/active").json()["program"]
    exercises = [item["exercise"] for day in program["days"] for item in day["exercises"]]
    assert exercises
    assert all(
        any(set(option) <= {"bodyweight"} for option in exercise["equipment_options"])
        for exercise in exercises
    )


def test_revisiting_onboarding_restores_weight_without_appending_placeholder(client: TestClient):
    register(client)
    complete_onboarding(client)

    restored = client.get("/api/v1/onboarding")
    assert restored.status_code == 200
    assert restored.json()["profile"]["weight_kg"] == 72.5
    assert restored.json()["profile"]["date_of_birth"] == "1998-04-12"

    step_one = {
        "step": 1,
        "data": {
            "full_name": "Aarav Mehta",
            "date_of_birth": "1998-04-12",
            "height_cm": 178,
            "weight_kg": 72.5,
            "gender": "male",
            "unit_system": "metric",
            "country": "India",
            "timezone": "Asia/Kolkata",
        },
    }
    assert client.put("/api/v1/onboarding", json=step_one).status_code == 200
    metrics = client.get("/api/v1/body-metrics").json()["items"]
    assert [item["weight_kg"] for item in metrics if item["weight_kg"] is not None] == [72.5]

    step_one["data"]["weight_kg"] = 68.4
    assert client.put("/api/v1/onboarding", json=step_one).status_code == 200
    dashboard = client.get("/api/v1/dashboard/today")
    assert dashboard.json()["metrics"]["weight_kg"] == 68.4

from fastapi.testclient import TestClient

from app.domains.workout_dataset import load_workout_dataset


def test_workbook_asset_contains_the_complete_normalized_module():
    dataset = load_workout_dataset()
    assert dataset["metadata"]["version"] == "1.0"
    assert dataset["metadata"]["counts"] == {
        "Split_Templates": 30,
        "Program_Days": 116,
        "Day_Exercises": 691,
        "Exercise_Catalog": 151,
        "Progression_Rules": 10,
        "Selection_Rules": 18,
        "Substitutions": 16,
        "Research_Sources": 8,
    }


def test_exercise_library_exposes_filters_pagination_and_dataset_coverage(client: TestClient):
    response = client.get("/api/v1/exercises", params={"page_size": 24})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 151
    assert len(payload["items"]) == 24
    assert payload["pages"] == 7
    assert payload["dataset"] == {
        "version": "1.0",
        "exercise_count": 151,
        "split_template_count": 30,
        "prescription_count": 691,
    }
    assert any(item["value"] == "Chest" for item in payload["facets"]["categories"])
    assert any(item["value"] == "bodyweight" for item in payload["facets"]["equipment"])

    filtered = client.get(
        "/api/v1/exercises",
        params={"q": "bench press", "category": "Chest", "compound": "true"},
    ).json()
    assert filtered["total"] >= 4
    assert all(item["category"] == "Chest" and item["is_compound"] for item in filtered["items"])


def test_exercise_detail_connects_prescriptions_substitutions_and_progression(client: TestClient):
    result = client.get("/api/v1/exercises", params={"q": "Barbell Bench Press"}).json()
    exercise = next(item for item in result["items"] if item["name"] == "Barbell Bench Press")
    detail_response = client.get(f"/api/v1/exercises/{exercise['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["exercise"]["source_id"] == "EX001"
    assert detail["exercise"]["equipment_display"] == "Barbell + Bench"
    assert detail["template_usage"]["total"] > 0
    assert detail["substitutions"][0]["group_id"] == "SUB01"
    assert any(rule["id"].startswith("PROG") for rule in detail["progression_rules"])

    overview = client.get("/api/v1/exercise-module").json()
    assert overview["counts"] == {
        "exercises": 151,
        "splits": 30,
        "day_templates": 116,
        "prescriptions": 691,
        "progression_rules": 10,
        "substitution_groups": 16,
    }
    assert len(overview["research_sources"]) == 8

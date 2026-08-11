import os
from pathlib import Path

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./athleteos_test.db"
os.environ["SESSION_SECRET"] = "test-only-session-secret-with-adequate-length"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.domains.catalog import seed_catalogues
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_catalogues(db)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    Path("athleteos_test.db").unlink(missing_ok=True)


def register(client: TestClient, email: str = "athlete@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Aarav Mehta",
            "email": email,
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
            "accept_terms": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def complete_onboarding(client: TestClient) -> None:
    steps = [
        {"step": 1, "data": {"full_name": "Aarav Mehta", "date_of_birth": "1998-04-12", "height_cm": 178, "weight_kg": 72.5, "gender": "male", "unit_system": "metric", "country": "India", "timezone": "Asia/Kolkata"}},
        {"step": 2, "data": {"water_target_ml": 3000, "sleep_hours": 7.5, "activity_level": "moderately_active"}},
        {"step": 3, "data": {"experience_level": "intermediate"}},
        {"step": 4, "data": {"training_type": "bodybuilding"}},
        {"step": 5, "data": {"primary_goal": "aesthetic_physique"}},
        {"step": 6, "data": {"equipment": ["full_gym"]}},
        {"step": 7, "data": {"days_per_week": 5, "preferred_weekdays": [0, 1, 2, 4, 5], "session_minutes": 60, "preferred_time": "evening"}},
        {"step": 8, "data": {"waist_cm": 80, "chest_cm": 98}},
        {"step": 9, "data": {"skip_scan": True, "cv_consent": False}},
    ]
    for step in steps:
        response = client.put("/api/v1/onboarding", json=step)
        assert response.status_code == 200, response.text

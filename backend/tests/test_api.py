import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ai_dependency"] is False
    assert data["mode"] == "deterministic"


def test_quick_calculator_endpoint():
    payload = {
        "present": 43,
        "total": 56,
        "future": 40,
        "target_percentage": 80.0
    }
    response = client.post("/api/calculate-quick", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["min_future_classes_to_attend"] == 34
    assert data["max_future_classes_can_skip"] == 6
    assert data["achievable"] is True


def test_quick_calculator_endpoint_invalid():
    # Present > Total
    payload = {
        "present": 60,
        "total": 56,
        "future": 40,
        "target_percentage": 80.0
    }
    response = client.post("/api/calculate-quick", json=payload)
    assert response.status_code == 400
    assert "cannot exceed" in response.json()["detail"]


def test_semester_project_endpoint():
    payload = {
        "target_percentage": 75.0,
        "start_date": "2026-10-01",
        "end_date": "2026-10-15",
        "weekdays": {
            "Monday": [{"subject": "Math", "periods": 2}],
            "Tuesday": [{"subject": "Physics", "periods": 1}],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": []
        },
        "no_class_dates": ["2026-10-05"],
        "special_working_days": [],
        "subjects": [
            {"name": "Math", "present": 10, "total": 12},
            {"name": "Physics", "present": 8, "total": 10}
        ]
    }
    response = client.post("/api/project", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["target_percentage"] == 75.0
    assert len(data["subjects"]) == 2
    math_res = next(s for s in data["subjects"] if s["name"] == "Math")
    assert math_res["achievable"] is True

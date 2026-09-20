import os
import sys

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "availability-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "availability-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_availability_all():
    response = client.get("/availability")
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    assert len(records) >= 6


def test_get_availability_filter_hotel():
    response = client.get("/availability?hotel_id=1")
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 2
    for r in records:
        assert r["hotel_id"] == 1


def test_get_availability_filter_room():
    response = client.get("/availability?room_id=3")
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["room_id"] == 3
    assert records[0]["available"] is False


def test_get_availability_by_room_id():
    response = client.get("/availability/1")
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == 1
    assert data["available"] is True


def test_get_availability_room_not_found():
    response = client.get("/availability/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Availability record not found"


def test_create_or_update_availability():
    payload = {"room_id": 99, "hotel_id": 10, "available": True}
    response = client.post("/availability", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == 99
    assert data["hotel_id"] == 10

    # Verify update on existing room
    update_payload = {"room_id": 99, "hotel_id": 10, "available": False}
    update_res = client.post("/availability", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["available"] is False

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
    assert response.json() == {"status": "healthy", "service": "booking-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "booking-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_bookings_list():
    response = client.get("/bookings")
    assert response.status_code == 200
    bookings = response.json()
    assert isinstance(bookings, list)
    assert len(bookings) >= 2


def test_create_booking():
    payload = {
        "user_id": 1,
        "hotel_id": 1,
        "room_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }
    response = client.post("/bookings", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["user_id"] == 1
    assert created["hotel_id"] == 1
    assert created["status"] == "PENDING"
    assert created["id"] >= 3


def test_get_booking_by_id():
    response = client.get("/bookings/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["status"] == "CONFIRMED"


def test_get_booking_not_found():
    response = client.get("/bookings/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found"


def test_update_booking_status_success():
    response = client.patch("/bookings/2/status", json={"status": "CONFIRMED"})
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


def test_update_booking_status_invalid():
    response = client.patch("/bookings/1/status", json={"status": "INVALID_STATUS"})
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_update_booking_status_not_found():
    response = client.patch("/bookings/9999/status", json={"status": "CANCELLED"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found"

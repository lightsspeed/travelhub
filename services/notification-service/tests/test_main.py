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
    assert response.json() == {"status": "healthy", "service": "notification-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "notification-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_notifications_list():
    response = client.get("/notifications")
    assert response.status_code == 200
    notifs = response.json()
    assert isinstance(notifs, list)
    assert len(notifs) >= 2


def test_get_notifications_filter_user():
    response = client.get("/notifications?user_id=1")
    assert response.status_code == 200
    notifs = response.json()
    assert len(notifs) == 1
    assert notifs[0]["user_id"] == 1


def test_get_notification_by_id():
    response = client.get("/notifications/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["status"] == "SENT"


def test_get_notification_not_found():
    response = client.get("/notifications/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"


def test_create_notification():
    payload = {
        "user_id": 1,
        "type": "BOOKING_CONFIRMED",
        "message": "Your booking is confirmed.",
    }
    response = client.post("/notifications", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["user_id"] == 1
    assert created["status"] == "PENDING"
    assert created["id"] >= 3


def test_update_notification_status_success():
    response = client.patch("/notifications/2/status", json={"status": "SENT"})
    assert response.status_code == 200
    assert response.json()["status"] == "SENT"


def test_update_notification_status_invalid():
    response = client.patch(
        "/notifications/1/status", json={"status": "INVALID_STATUS"}
    )
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_update_notification_status_not_found():
    response = client.patch("/notifications/9999/status", json={"status": "FAILED"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"

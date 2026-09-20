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
    assert response.json() == {"status": "healthy", "service": "room-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "room-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_rooms_collection():
    response = client.get("/rooms")
    assert response.status_code == 200
    rooms = response.json()
    assert isinstance(rooms, list)
    assert len(rooms) >= 6


def test_get_room_by_id():
    response = client.get("/rooms/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["hotel_id"] == 1
    assert "room_type" in data
    assert "price_per_night" in data


def test_get_room_not_found():
    response = client.get("/rooms/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


def test_get_rooms_by_hotel():
    response = client.get("/hotels/1/rooms")
    assert response.status_code == 200
    hotel_rooms = response.json()
    assert isinstance(hotel_rooms, list)
    assert len(hotel_rooms) >= 2
    for room in hotel_rooms:
        assert room["hotel_id"] == 1


def test_create_room():
    payload = {
        "hotel_id": 4,
        "room_type": "Executive Penthouse",
        "capacity": 4,
        "price_per_night": 750.0,
        "currency": "USD",
        "available": True,
    }
    response = client.post("/rooms", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["hotel_id"] == 4
    assert created["room_type"] == "Executive Penthouse"
    assert created["id"] >= 7

    # Verify room exists in collection
    get_res = client.get(f"/rooms/{created['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["price_per_night"] == 750.0

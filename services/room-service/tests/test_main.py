import os
import sys
from unittest.mock import MagicMock, patch

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
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


# --- Tests for the new GET /rooms/{room_id}/hotel endpoint ---

def _mock_hotel_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a fake httpx response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = body or {}
    return mock_resp


MOCK_HOTEL = {
    "id": 1,
    "name": "The Grand Mumbai",
    "city": "Mumbai",
    "country": "India",
    "description": "Luxury hotel near Marine Drive with breathtaking ocean views.",
    "rating": 4.8,
}


def test_get_room_with_hotel_success():
    """room exists + hotel-service returns 200 → 200 with room and hotel."""
    with patch("httpx.get", return_value=_mock_hotel_response(200, MOCK_HOTEL)):
        response = client.get("/rooms/1/hotel")
    assert response.status_code == 200
    data = response.json()
    assert "room" in data
    assert "hotel" in data
    assert data["room"]["id"] == 1
    assert data["hotel"]["name"] == "The Grand Mumbai"


def test_get_room_with_hotel_contains_both_fields():
    """Successful response contains all expected room and hotel fields."""
    with patch("httpx.get", return_value=_mock_hotel_response(200, MOCK_HOTEL)):
        response = client.get("/rooms/1/hotel")
    assert response.status_code == 200
    data = response.json()
    room = data["room"]
    hotel = data["hotel"]
    assert "room_type" in room
    assert "price_per_night" in room
    assert "hotel_id" in room
    assert "city" in hotel
    assert "rating" in hotel


def test_get_room_with_hotel_room_not_found():
    """Room does not exist → 404 without calling hotel-service."""
    with patch("httpx.get") as mock_get:
        response = client.get("/rooms/9999/hotel")
    assert response.status_code == 404
    assert "Room not found" in response.json()["detail"]
    mock_get.assert_not_called()


def test_get_room_with_hotel_upstream_404():
    """hotel-service returns 404 for the hotel_id → room-service returns 404."""
    with patch("httpx.get", return_value=_mock_hotel_response(404)):
        response = client.get("/rooms/1/hotel")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_room_with_hotel_service_unavailable():
    """hotel-service connection fails → room-service returns 503."""
    with patch("httpx.get", side_effect=httpx.RequestError("connection refused")):
        response = client.get("/rooms/1/hotel")
    assert response.status_code == 503
    assert response.json()["detail"] == "Hotel service unavailable"


def test_get_room_with_hotel_timeout():
    """hotel-service times out → room-service returns 503."""
    with patch("httpx.get", side_effect=httpx.TimeoutException("timed out")):
        response = client.get("/rooms/1/hotel")
    assert response.status_code == 503
    assert response.json()["detail"] == "Hotel service unavailable"

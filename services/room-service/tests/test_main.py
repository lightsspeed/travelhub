import os
import sys
from unittest.mock import MagicMock, patch

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_mock_rooms = [
    {
        "id": 1,
        "hotel_id": 1,
        "room_type": "Deluxe Sea View Suite",
        "capacity": 2,
        "price_per_night": 250.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 2,
        "hotel_id": 1,
        "room_type": "Superior City View Room",
        "capacity": 2,
        "price_per_night": 150.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 3,
        "hotel_id": 2,
        "room_type": "Beachfront Villa",
        "capacity": 4,
        "price_per_night": 320.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 4,
        "hotel_id": 2,
        "room_type": "Garden Cottage",
        "capacity": 2,
        "price_per_night": 120.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 5,
        "hotel_id": 3,
        "room_type": "Skyline Luxury Suite",
        "capacity": 3,
        "price_per_night": 450.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 6,
        "hotel_id": 4,
        "room_type": "Marina Bay View Room",
        "capacity": 2,
        "price_per_night": 280.0,
        "currency": "USD",
        "available": True,
    },
]


class _MockCursor:
    def __init__(self):
        self._last_query = ""
        self._args = ()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query, args=()):
        self._last_query = str(query)
        self._args = args
        if "INSERT INTO rooms" in self._last_query:
            _mock_rooms.append({
                "id": args[0],
                "hotel_id": args[1],
                "room_type": args[2],
                "capacity": args[3],
                "price_per_night": args[4],
                "currency": args[5],
                "available": args[6],
            })

    def fetchone(self):
        q = self._last_query.strip()
        if "SELECT 1" in q:
            return (1,)
        if "SELECT COUNT" in q:
            return (len(_mock_rooms),)
        if "SELECT COALESCE(MAX(id)" in q:
            max_id = max([r["id"] for r in _mock_rooms], default=0)
            return (max_id,)
        if "WHERE id =" in q:
            room_id = self._args[0]
            for r in _mock_rooms:
                if r["id"] == room_id:
                    return (
                        r["id"],
                        r["hotel_id"],
                        r["room_type"],
                        r["capacity"],
                        r["price_per_night"],
                        r["currency"],
                        r["available"],
                    )
            return None
        return None

    def fetchall(self):
        q = self._last_query.strip()
        if "WHERE hotel_id =" in q:
            hotel_id = self._args[0]
            return [
                (
                    r["id"],
                    r["hotel_id"],
                    r["room_type"],
                    r["capacity"],
                    r["price_per_night"],
                    r["currency"],
                    r["available"],
                )
                for r in _mock_rooms
                if r["hotel_id"] == hotel_id
            ]
        if "SELECT id, hotel_id, room_type" in q:
            return [
                (
                    r["id"],
                    r["hotel_id"],
                    r["room_type"],
                    r["capacity"],
                    r["price_per_night"],
                    r["currency"],
                    r["available"],
                )
                for r in _mock_rooms
            ]
        return []


class _MockConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def cursor(self):
        return _MockCursor()

    def commit(self):
        pass

    def close(self):
        pass


def _get_test_db_connection():
    if os.getenv("TEST_USE_REAL_DB") == "true":
        import psycopg
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://travelhub_room:roompass@localhost:5432/room_db",
        )
        return psycopg.connect(db_url, connect_timeout=2)
    return _MockConnection()


# Apply patch BEFORE initializing TestClient
patch("app.main.get_db_connection", side_effect=_get_test_db_connection).start()

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
    assert response.status_code in (200, 201)
    created = response.json()
    assert created["hotel_id"] == 4
    assert created["room_type"] == "Executive Penthouse"


# --- Tests for GET /rooms/{room_id}/hotel endpoint ---

def _mock_hotel_response(status_code: int, body: dict | None = None) -> MagicMock:
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
    with patch("httpx.get") as mock_get:
        response = client.get("/rooms/9999/hotel")
    assert response.status_code == 404
    assert "Room not found" in response.json()["detail"]
    mock_get.assert_not_called()


def test_get_room_with_hotel_upstream_404():
    with patch("httpx.get", return_value=_mock_hotel_response(404)):
        response = client.get("/rooms/1/hotel")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_room_with_hotel_service_unavailable():
    with patch("httpx.get", side_effect=httpx.RequestError("connection refused")):
        response = client.get("/rooms/1/hotel")
    assert response.status_code == 503
    assert response.json()["detail"] == "Hotel service unavailable"


def test_get_room_with_hotel_timeout():
    with patch("httpx.get", side_effect=httpx.TimeoutException("timed out")):
        response = client.get("/rooms/1/hotel")
    assert response.status_code == 503
    assert response.json()["detail"] == "Hotel service unavailable"

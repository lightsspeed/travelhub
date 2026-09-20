import os
import sys
from unittest.mock import patch

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_mock_hotels = [
    {
        "id": 1,
        "name": "The Grand Mumbai",
        "city": "Mumbai",
        "country": "India",
        "description": "Luxury hotel near Marine Drive with breathtaking ocean views.",
        "rating": 4.8,
    },
    {
        "id": 2,
        "name": "Goa Beachfront Resort",
        "city": "Goa",
        "country": "India",
        "description": "Tranquil resort with private beach access and Portuguese architecture.",
        "rating": 4.6,
    },
    {
        "id": 3,
        "name": "Dubai Oasis Hotel",
        "city": "Dubai",
        "country": "UAE",
        "description": "Iconic skyline views with world-class dining and luxury amenities.",
        "rating": 4.9,
    },
    {
        "id": 4,
        "name": "Marina Bay Vista",
        "city": "Singapore",
        "country": "Singapore",
        "description": "Contemporary waterfront hotel overlooking Marina Bay.",
        "rating": 4.7,
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
        if "INSERT INTO hotels" in self._last_query:
            _mock_hotels.append({
                "id": args[0],
                "name": args[1],
                "city": args[2],
                "country": args[3],
                "description": args[4],
                "rating": args[5],
            })

    def fetchone(self):
        q = self._last_query.strip()
        if "SELECT 1" in q:
            return (1,)
        if "SELECT COUNT" in q:
            return (len(_mock_hotels),)
        if "SELECT COALESCE(MAX(id)" in q:
            max_id = max([h["id"] for h in _mock_hotels], default=0)
            return (max_id,)
        if "WHERE id =" in q:
            hotel_id = self._args[0]
            for h in _mock_hotels:
                if h["id"] == hotel_id:
                    return (
                        h["id"],
                        h["name"],
                        h["city"],
                        h["country"],
                        h["description"],
                        h["rating"],
                    )
            return None
        return None

    def fetchall(self):
        q = self._last_query.strip()
        if "SELECT id, name, city, country, description, rating FROM hotels" in q:
            return [
                (
                    h["id"],
                    h["name"],
                    h["city"],
                    h["country"],
                    h["description"],
                    h["rating"],
                )
                for h in _mock_hotels
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
            "postgresql://travelhub_hotel:hotelpass@localhost:5432/hotel_db",
        )
        return psycopg.connect(db_url, connect_timeout=2)
    return _MockConnection()


# Apply patch BEFORE initializing TestClient
patch("app.main.get_db_connection", side_effect=_get_test_db_connection).start()

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "hotel-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "hotel-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_hotels_collection():
    response = client.get("/hotels")
    assert response.status_code == 200
    hotels = response.json()
    assert isinstance(hotels, list)
    assert len(hotels) >= 4


def test_get_hotel_by_id():
    response = client.get("/hotels/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "The Grand Mumbai"


def test_get_hotel_not_found():
    response = client.get("/hotels/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Hotel not found"


def test_create_hotel():
    payload = {
        "name": "New Hotel",
        "city": "London",
        "country": "UK",
        "description": "Lovely boutique hotel.",
        "rating": 4.5,
    }
    response = client.post("/hotels", json=payload)
    assert response.status_code in (200, 201)
    created = response.json()
    assert created["name"] == "New Hotel"
    assert created["city"] == "London"
    assert "id" in created

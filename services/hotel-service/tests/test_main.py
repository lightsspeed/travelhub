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
    assert data["city"] == "Mumbai"
    assert "name" in data
    assert "rating" in data


def test_get_hotel_not_found():
    response = client.get("/hotels/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Hotel not found"


def test_create_hotel():
    payload = {
        "name": "Tokyo Garden Hotel",
        "city": "Tokyo",
        "country": "Japan",
        "description": "Modern hotel in Shinjuku with city views.",
        "rating": 4.5,
    }
    response = client.post("/hotels", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Tokyo Garden Hotel"
    assert created["city"] == "Tokyo"
    assert created["id"] >= 5

    # Verify hotel exists in collection
    get_res = client.get(f"/hotels/{created['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["country"] == "Japan"

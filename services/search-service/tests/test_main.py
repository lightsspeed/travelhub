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
    assert response.json() == {"status": "healthy", "service": "search-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "search-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_search_without_filters():
    response = client.get("/search")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) >= 4


def test_search_by_city():
    response = client.get("/search?city=Mumbai")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "The Grand Mumbai"


def test_search_by_country():
    response = client.get("/search?country=India")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2


def test_search_by_city_and_country():
    response = client.get("/search?city=Goa&country=India")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["city"] == "Goa"


def test_search_no_match():
    response = client.get("/search?city=NonExistentCity")
    assert response.status_code == 200
    assert response.json() == []


def test_get_search_hotel_by_id():
    response = client.get("/search/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "The Grand Mumbai"


def test_get_search_hotel_not_found():
    response = client.get("/search/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Hotel not found"

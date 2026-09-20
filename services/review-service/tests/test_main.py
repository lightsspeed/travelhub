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
    assert response.json() == {"status": "healthy", "service": "review-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "review-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_reviews_list():
    response = client.get("/reviews")
    assert response.status_code == 200
    reviews = response.json()
    assert isinstance(reviews, list)
    assert len(reviews) >= 3


def test_get_reviews_filter_hotel():
    response = client.get("/reviews?hotel_id=1")
    assert response.status_code == 200
    reviews = response.json()
    assert len(reviews) == 2
    for r in reviews:
        assert r["hotel_id"] == 1


def test_get_reviews_filter_user():
    response = client.get("/reviews?user_id=1")
    assert response.status_code == 200
    reviews = response.json()
    assert len(reviews) == 1
    assert reviews[0]["user_id"] == 1


def test_get_review_by_id():
    response = client.get("/reviews/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["rating"] == 5


def test_get_review_not_found():
    response = client.get("/reviews/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Review not found"


def test_create_review_success():
    payload = {
        "user_id": 1,
        "hotel_id": 1,
        "rating": 5,
        "comment": "Excellent stay",
    }
    response = client.post("/reviews", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["user_id"] == 1
    assert created["rating"] == 5
    assert created["id"] >= 4


def test_create_review_invalid_rating():
    payload = {
        "user_id": 1,
        "hotel_id": 1,
        "rating": 6,
        "comment": "Invalid rating test",
    }
    response = client.post("/reviews", json=payload)
    assert response.status_code == 400
    assert "Rating must be between 1 and 5" in response.json()["detail"]

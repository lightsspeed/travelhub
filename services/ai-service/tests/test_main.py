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
    assert response.json() == {"status": "healthy", "service": "ai-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "ai-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_assistant_request():
    payload = {"message": "Find me a hotel in Mumbai"}
    response = client.post("/assistant", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Find me a hotel in Mumbai"
    assert (
        data["response"]
        == "I can help you search hotels, check availability, and manage bookings."
    )


def test_get_conversations():
    response = client.get("/conversations")
    assert response.status_code == 200
    conversations = response.json()
    assert isinstance(conversations, list)
    assert len(conversations) >= 1

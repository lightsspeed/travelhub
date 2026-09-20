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
    assert response.json() == {"status": "healthy", "service": "payment-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "payment-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_payments_list():
    response = client.get("/payments")
    assert response.status_code == 200
    payments = response.json()
    assert isinstance(payments, list)
    assert len(payments) >= 2


def test_create_payment_success():
    payload = {"booking_id": 1, "amount": 500.0, "currency": "USD"}
    response = client.post("/payments", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["booking_id"] == 1
    assert created["amount"] == 500.0
    assert created["status"] == "SUCCESS"
    assert created["id"] >= 3


def test_create_payment_invalid_amount():
    payload = {"booking_id": 1, "amount": -50.0, "currency": "USD"}
    response = client.post("/payments", json=payload)
    assert response.status_code == 400
    assert "Amount must be greater than zero" in response.json()["detail"]


def test_get_payment_by_id():
    response = client.get("/payments/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["amount"] == 500.0


def test_get_payment_not_found():
    response = client.get("/payments/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"

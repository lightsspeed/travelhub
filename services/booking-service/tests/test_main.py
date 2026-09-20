from concurrent.futures import ThreadPoolExecutor
import os
import sys
import time
from unittest.mock import MagicMock, patch

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
import httpx
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "booking-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "booking-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_bookings_list():
    response = client.get("/bookings")
    assert response.status_code == 200
    bookings = response.json()
    assert isinstance(bookings, list)
    assert len(bookings) >= 2


def test_get_booking_by_id():
    response = client.get("/bookings/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["status"] == "CONFIRMED"


def test_get_booking_not_found():
    response = client.get("/bookings/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found"


def test_update_booking_status_success():
    response = client.patch("/bookings/2/status", json={"status": "CONFIRMED"})
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


def test_update_booking_status_invalid():
    response = client.patch("/bookings/1/status", json={"status": "INVALID_STATUS"})
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_update_booking_status_not_found():
    response = client.patch("/bookings/9999/status", json={"status": "CANCELLED"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Booking not found"


@patch("httpx.post")
def test_booking_succeeds_when_room_available(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "room_id": 101,
        "available": False,
        "status": "reserved",
    }
    mock_post.return_value = mock_resp

    payload = {
        "user_id": 1,
        "room_id": 101,
        "hotel_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }
    response = client.post("/bookings", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["user_id"] == 1
    assert created["room_id"] == 101
    assert created["status"] == "CONFIRMED"


@patch("httpx.post")
def test_booking_fails_when_room_unavailable(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 409
    mock_resp.json.return_value = {"detail": "Room is not available"}
    mock_post.return_value = mock_resp

    payload = {"user_id": 1, "room_id": 3}
    response = client.post("/bookings", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "Room is not available"


@patch("httpx.post")
def test_booking_fails_when_room_does_not_exist(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"detail": "Room not found"}
    mock_post.return_value = mock_resp

    payload = {"user_id": 1, "room_id": 9999}
    response = client.post("/bookings", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


@patch("httpx.post")
def test_booking_returns_503_when_availability_service_unavailable(mock_post):
    mock_post.side_effect = httpx.RequestError("Connection failed")

    payload = {"user_id": 1, "room_id": 101}
    response = client.post("/bookings", json=payload)
    assert response.status_code == 503
    assert response.json()["detail"] == "Availability service unavailable"


@patch("httpx.post")
def test_idempotency_key_first_request_and_retry(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "room_id": 50,
        "available": False,
        "status": "reserved",
    }
    mock_post.return_value = mock_resp

    headers = {"Idempotency-Key": "test-key-001"}
    payload = {
        "user_id": 10,
        "room_id": 50,
        "hotel_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }

    # First request
    res1 = client.post("/bookings", json=payload, headers=headers)
    assert res1.status_code == 201
    booking1 = res1.json()
    assert mock_post.call_count == 1

    # Retry request with same key and same payload
    res2 = client.post("/bookings", json=payload, headers=headers)
    assert res2.status_code == 201
    booking2 = res2.json()
    assert booking2 == booking1
    # Verify availability-service was NOT called again
    assert mock_post.call_count == 1


@patch("httpx.post")
def test_idempotency_key_different_payload_returns_409(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "room_id": 60,
        "available": False,
        "status": "reserved",
    }
    mock_post.return_value = mock_resp

    headers = {"Idempotency-Key": "test-key-reuse"}
    payload1 = {
        "user_id": 10,
        "room_id": 60,
        "hotel_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }
    payload2 = {
        "user_id": 99,
        "room_id": 60,
        "hotel_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }

    # First request
    res1 = client.post("/bookings", json=payload1, headers=headers)
    assert res1.status_code == 201

    # Second request with SAME key but DIFFERENT payload
    res2 = client.post("/bookings", json=payload2, headers=headers)
    assert res2.status_code == 409
    assert (
        res2.json()["detail"]
        == "Idempotency key already used for a different request"
    )


@patch("httpx.post")
def test_different_idempotency_keys_create_separate_bookings(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "room_id": 70,
        "available": False,
        "status": "reserved",
    }
    mock_post.return_value = mock_resp

    payload1 = {
        "user_id": 1,
        "room_id": 70,
        "hotel_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }
    payload2 = {
        "user_id": 2,
        "room_id": 71,
        "hotel_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }

    res1 = client.post(
        "/bookings", json=payload1, headers={"Idempotency-Key": "key-A"}
    )
    res2 = client.post(
        "/bookings", json=payload2, headers={"Idempotency-Key": "key-B"}
    )

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["id"] != res2.json()["id"]


@patch("httpx.post")
def test_concurrent_identical_idempotent_requests(mock_post):
    def slow_reserve(*args, **kwargs):
        time.sleep(0.1)  # Simulate downstream network delay
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "room_id": 99,
            "available": False,
            "status": "reserved",
        }
        return mock_resp

    mock_post.side_effect = slow_reserve

    payload = {
        "user_id": 10,
        "room_id": 99,
        "hotel_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }
    headers = {"Idempotency-Key": "concurrent-unit-key"}

    def make_req():
        return client.post("/bookings", json=payload, headers=headers)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(make_req)
        f2 = executor.submit(make_req)
        res1 = f1.result()
        res2 = f2.result()

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json() == res2.json()
    assert res1.json()["id"] == res2.json()["id"]
    assert mock_post.call_count == 1


@patch("httpx.post")
def test_failed_first_idempotent_request_allows_later_retry(mock_post):
    # First call fails (e.g. 503)
    fail_resp = MagicMock()
    fail_resp.status_code = 503
    mock_post.return_value = fail_resp

    headers = {"Idempotency-Key": "retry-after-fail-key"}
    payload = {
        "user_id": 10,
        "room_id": 88,
        "hotel_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
    }

    res1 = client.post("/bookings", json=payload, headers=headers)
    assert res1.status_code == 503

    # Now downstream service succeeds (200 OK)
    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.json.return_value = {
        "room_id": 88,
        "available": False,
        "status": "reserved",
    }
    mock_post.return_value = success_resp

    res2 = client.post("/bookings", json=payload, headers=headers)
    assert res2.status_code == 201
    assert res2.json()["user_id"] == 10

import os
import sys
from unittest.mock import patch

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_mock_availability = [
    {"room_id": 1, "available": True},
    {"room_id": 2, "available": True},
    {"room_id": 3, "available": False},
    {"room_id": 4, "available": True},
    {"room_id": 5, "available": True},
    {"room_id": 6, "available": False},
]


class _MockCursor:
    def __init__(self):
        self._last_query = ""
        self._args = ()
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query, args=()):
        self._last_query = str(query)
        self._args = args
        self.rowcount = 0
        if "INSERT INTO availability" in self._last_query:
            room_id = args[0]
            avail = args[1]
            found = False
            for rec in _mock_availability:
                if rec["room_id"] == room_id:
                    rec["available"] = avail
                    found = True
                    break
            if not found:
                _mock_availability.append({"room_id": room_id, "available": avail})
            self.rowcount = 1
        elif "UPDATE availability" in self._last_query:
            room_id = args[0]
            # Release: SET available = true WHERE available = false
            if "SET available = true" in self._last_query:
                for rec in _mock_availability:
                    if rec["room_id"] == room_id:
                        if rec["available"] is False:
                            rec["available"] = True
                            self.rowcount = 1
                        else:
                            self.rowcount = 0
                        break
            # Reserve: SET available = false WHERE available = true
            else:
                for rec in _mock_availability:
                    if rec["room_id"] == room_id:
                        if rec["available"] is True:
                            rec["available"] = False
                            self.rowcount = 1
                        else:
                            self.rowcount = 0
                        break

    def fetchone(self):
        q = self._last_query.strip()
        if "SELECT 1" in q:
            return (1,)
        if "SELECT COUNT" in q:
            return (len(_mock_availability),)
        if "WHERE room_id =" in q:
            room_id = self._args[0]
            for rec in _mock_availability:
                if rec["room_id"] == room_id:
                    return (rec["room_id"], rec["available"])
            return None
        return None

    def fetchall(self):
        q = self._last_query.strip()
        if "SELECT room_id, available FROM availability WHERE room_id =" in q:
            room_id = self._args[0]
            return [
                (rec["room_id"], rec["available"])
                for rec in _mock_availability
                if rec["room_id"] == room_id
            ]
        if "SELECT room_id, available FROM availability" in q:
            return [(rec["room_id"], rec["available"]) for rec in _mock_availability]
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
            "postgresql://travelhub_availability:availabilitypass@localhost:5432/availability_db",
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
    assert response.json() == {"status": "healthy", "service": "availability-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "availability-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_availability_all():
    response = client.get("/availability")
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    assert len(records) >= 6


def test_get_availability_filter_room():
    response = client.get("/availability?room_id=3")
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0]["room_id"] == 3
    assert records[0]["available"] is False


def test_get_availability_by_room_id():
    response = client.get("/availability/1")
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == 1
    assert data["available"] is True


def test_get_availability_room_not_found():
    response = client.get("/availability/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Availability record not found"


def test_create_or_update_availability():
    payload = {"room_id": 99, "available": True}
    response = client.post("/availability", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == 99
    assert data["available"] is True


def test_reserve_available_room_succeeds():
    response = client.post("/availability/4/reserve", json={"booking_id": 1001})
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == 4
    assert data["available"] is False
    assert data["booking_id"] == 1001


def test_reserve_unavailable_room_returns_409():
    response = client.post("/availability/3/reserve", json={"booking_id": 1002})
    assert response.status_code == 409
    assert response.json()["detail"] == "Room is not available"


def test_reserve_nonexistent_room_returns_404():
    response = client.post("/availability/8888/reserve", json={"booking_id": 1003})
    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


def test_reserve_changes_availability_to_false():
    # Room 5 is currently available
    get_res = client.get("/availability/5")
    assert get_res.status_code == 200
    assert get_res.json()["available"] is True

    # Reserve room 5
    res_response = client.post("/availability/5/reserve", json={"booking_id": 1004})
    assert res_response.status_code == 200

    # Verify room 5 is now unavailable
    get_res_after = client.get("/availability/5")
    assert get_res_after.status_code == 200
    assert get_res_after.json()["available"] is False


def test_reserve_consecutive_attempt_returns_409():
    # First attempt on available room 1
    res1 = client.post("/availability/1/reserve", json={"booking_id": 2001})
    assert res1.status_code == 200

    # Second attempt on room 1 (now unavailable)
    res2 = client.post("/availability/1/reserve", json={"booking_id": 2002})
    assert res2.status_code == 409
    assert res2.json()["detail"] == "Room is not available"


# -------------------------------------------------------------------
# Phase 9 Part 2 — Release endpoint tests
# -------------------------------------------------------------------

def test_release_unavailable_room_succeeds():
    """Releasing a currently reserved room returns 200 and marks it available."""
    # Room 3 is seeded as unavailable in _mock_availability
    response = client.post("/availability/3/release")
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == 3
    assert data["available"] is True
    assert data["status"] == "released"

    # Verify persistence via GET
    get_res = client.get("/availability/3")
    assert get_res.status_code == 200
    assert get_res.json()["available"] is True


def test_release_nonexistent_room_returns_404():
    """Releasing a room that does not exist returns 404."""
    response = client.post("/availability/9999/release")
    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


def test_release_already_available_room_is_safe():
    """Releasing a room that is already available is idempotent — returns 200."""
    # Room 2 is seeded as available; ensure it is still available
    get_res = client.get("/availability/2")
    assert get_res.status_code == 200
    assert get_res.json()["available"] is True

    response = client.post("/availability/2/release")
    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == 2
    assert data["available"] is True
    assert data["status"] == "already_available"


def test_release_persists_in_mock_db():
    """Reserve a room then release it — state returns to available."""
    # Room 6 is seeded as unavailable; release it
    rel = client.post("/availability/6/release")
    assert rel.status_code == 200
    assert rel.json()["status"] == "released"

    # Now re-reserve it to confirm it is available again
    res = client.post("/availability/6/reserve", json={"booking_id": 3001})
    assert res.status_code == 200
    assert res.json()["available"] is False


# -------------------------------------------------------------------
# Phase 9 Part 3 — Idempotent release (timeout-safe retry)
# -------------------------------------------------------------------

def test_release_idempotent_triple_call():
    """Release the same room three times:
    - first call:  released
    - second call: already_available
    - third call:  already_available
    State must not be corrupted by repeated release calls.
    """
    # First: make room 2 unavailable via reserve
    # (room 2 was reset to available by earlier tests — reserve it first)
    reserve_res = client.post("/availability/2/reserve", json={"booking_id": 9001})
    assert reserve_res.status_code == 200
    assert reserve_res.json()["available"] is False

    # First release
    rel1 = client.post("/availability/2/release")
    assert rel1.status_code == 200
    assert rel1.json()["status"] == "released"
    assert rel1.json()["available"] is True

    # Verify state after first release
    state1 = client.get("/availability/2")
    assert state1.json()["available"] is True

    # Second release (idempotent — already available)
    rel2 = client.post("/availability/2/release")
    assert rel2.status_code == 200
    assert rel2.json()["status"] == "already_available"
    assert rel2.json()["available"] is True

    # State unchanged
    state2 = client.get("/availability/2")
    assert state2.json()["available"] is True

    # Third release (still idempotent)
    rel3 = client.post("/availability/2/release")
    assert rel3.status_code == 200
    assert rel3.json()["status"] == "already_available"
    assert rel3.json()["available"] is True

    # Final state: still available — no corruption
    state3 = client.get("/availability/2")
    assert state3.json()["available"] is True


def test_release_nonexistent_room_always_returns_404():
    """Releasing a non-existent room always returns 404, never creates state."""
    for _ in range(3):
        resp = client.post("/availability/7777/release")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Room not found"


def test_release_after_reserve_cycle():
    """Full cycle: reserve → release → verify available.
    Demonstrates the compensation pattern without retry in isolation.
    """
    # Ensure room 4 is available (re-reserve then release to guarantee state)
    # Step 1: reserve
    res = client.post("/availability/4/reserve", json={"booking_id": 9002})
    # room 4 may already be unavailable — handle both cases
    if res.status_code == 409:
        # Already unavailable — release it
        pass
    else:
        assert res.status_code == 200
        assert res.json()["available"] is False

    # Step 2: release (compensation)
    rel = client.post("/availability/4/release")
    assert rel.status_code == 200
    assert rel.json()["available"] is True

    # Step 3: verify via GET
    get_res = client.get("/availability/4")
    assert get_res.json()["available"] is True

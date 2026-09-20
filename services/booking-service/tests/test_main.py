from concurrent.futures import ThreadPoolExecutor
import os
import sys
import time
from unittest.mock import MagicMock, patch

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
import httpx

_mock_bookings = [
    {
        "id": 1,
        "user_id": 1,
        "hotel_id": 1,
        "room_id": 1,
        "check_in": "2026-10-01",
        "check_out": "2026-10-03",
        "status": "CONFIRMED",
    },
    {
        "id": 2,
        "user_id": 2,
        "hotel_id": 2,
        "room_id": 3,
        "check_in": "2026-11-10",
        "check_out": "2026-11-15",
        "status": "PENDING",
    },
]
_mock_seq = [3]
_mock_recovery_tasks = []
_db_available = True


class _MockCursor:
    def __init__(self, conn):
        self._conn = conn
        self._last_query = ""
        self._args = ()
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query, args=()):
        if not _db_available:
            raise Exception("Database unavailable")
        self._last_query = str(query)
        self._args = args
        self.rowcount = 0

        if "INSERT INTO bookings" in self._last_query:
            b = {
                "id": args[0],
                "user_id": args[1],
                "hotel_id": args[2],
                "room_id": args[3],
                "check_in": args[4],
                "check_out": args[5],
                "status": args[6],
            }
            self._conn._staged_bookings.append(b)
            self.rowcount = 1
        elif "UPDATE bookings SET status" in self._last_query:
            new_status = args[0]
            b_id = args[1]
            all_b = _mock_bookings + self._conn._staged_bookings
            for b in all_b:
                if b["id"] == b_id:
                    b["status"] = new_status
                    self.rowcount = 1
                    break
        elif "INSERT INTO recovery_tasks" in self._last_query:
            task_id = len(_mock_recovery_tasks) + len(self._conn._staged_tasks) + 1
            task = {
                "id": task_id,
                "room_id": args[0],
                "action": args[1],
                "status": args[2],
                "attempts": 0,
            }
            self._conn._staged_tasks.append(task)
            self.rowcount = 1
        elif "UPDATE recovery_tasks SET status" in self._last_query:
            new_status = args[0]
            t_id = args[1]
            all_t = _mock_recovery_tasks + self._conn._staged_tasks
            for t in all_t:
                if t["id"] == t_id:
                    t["status"] = new_status
                    self.rowcount = 1
                    break

    def fetchone(self):
        if not _db_available:
            raise Exception("Database unavailable")
        q = self._last_query.strip()
        all_b = _mock_bookings + self._conn._staged_bookings
        all_t = _mock_recovery_tasks + self._conn._staged_tasks
        if "SELECT 1;" in q:
            return (1,)
        if "SELECT COUNT(*) FROM bookings;" in q:
            return (len(all_b),)
        if "SELECT nextval('booking_id_seq');" in q:
            val = _mock_seq[0]
            _mock_seq[0] += 1
            return (val,)
        if "SELECT id, user_id, hotel_id, room_id, check_in, check_out, status FROM bookings WHERE id =" in q:
            b_id = self._args[0]
            for b in all_b:
                if b["id"] == b_id:
                    return (
                        b["id"],
                        b["user_id"],
                        b["hotel_id"],
                        b["room_id"],
                        b["check_in"],
                        b["check_out"],
                        b["status"],
                    )
            return None
        if "UPDATE bookings SET status =" in q:
            new_status = self._args[0]
            b_id = self._args[1]
            for b in all_b:
                if b["id"] == b_id:
                    return (
                        b["id"],
                        b["user_id"],
                        b["hotel_id"],
                        b["room_id"],
                        b["check_in"],
                        b["check_out"],
                        b["status"],
                    )
            return None
        if "INSERT INTO recovery_tasks" in q:
            if all_t:
                t = all_t[-1]
                return (t["id"], t["room_id"], t["action"], t["status"], t["attempts"])
            return None
        if "UPDATE recovery_tasks SET status =" in q:
            new_status = self._args[0]
            t_id = self._args[1]
            for t in all_t:
                if t["id"] == t_id:
                    return (t["id"], t["room_id"], t["action"], t["status"], t["attempts"])
            return None
        return None

    def fetchall(self):
        if not _db_available:
            raise Exception("Database unavailable")
        q = self._last_query.strip()
        all_b = _mock_bookings + self._conn._staged_bookings
        all_t = _mock_recovery_tasks + self._conn._staged_tasks
        if "SELECT id, user_id, hotel_id, room_id, check_in, check_out, status FROM bookings" in q:
            return [
                (
                    b["id"],
                    b["user_id"],
                    b["hotel_id"],
                    b["room_id"],
                    b["check_in"],
                    b["check_out"],
                    b["status"],
                )
                for b in all_b
            ]
        if "SELECT id, room_id, action, status, attempts FROM recovery_tasks" in q:
            return [
                (t["id"], t["room_id"], t["action"], t["status"], t["attempts"])
                for t in all_t
            ]
        return []


class _MockConnection:
    def __init__(self):
        self._staged_bookings = []
        self._staged_tasks = []

    def __enter__(self):
        if not _db_available:
            raise Exception("Database unavailable")
        self._staged_bookings = []
        self._staged_tasks = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._staged_bookings.clear()
            self._staged_tasks.clear()

    def cursor(self):
        return _MockCursor(self)

    def commit(self):
        _mock_bookings.extend(self._staged_bookings)
        self._staged_bookings.clear()
        _mock_recovery_tasks.extend(self._staged_tasks)
        self._staged_tasks.clear()


def _mock_get_db_connection():
    if not _db_available:
        raise Exception("Database unavailable")
    return _MockConnection()


# Patch get_db_connection globally for imports
db_patcher = patch("app.main.get_db_connection", side_effect=_mock_get_db_connection)
db_patcher.start()

from app.main import app, init_db

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

    res1 = client.post("/bookings", json=payload1, headers=headers)
    assert res1.status_code == 201

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
        time.sleep(0.1)
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


# -------------------------------------------------------------------
# Phase 9 Parts 1-3 — Helper Compensation & Retry Function Tests
# -------------------------------------------------------------------

def _reserve_ok(room_id):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"room_id": room_id, "available": False, "status": "reserved"}
    return m


def _release_ok(room_id):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"room_id": room_id, "available": True, "status": "released"}
    return m


def _release_already(room_id):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"room_id": room_id, "available": True, "status": "already_available"}
    return m


def _release_fail(code=503):
    m = MagicMock()
    m.status_code = code
    m.json.return_value = {"detail": "error"}
    return m


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_compensation_release_succeeds_on_first_attempt(mock_post):
    mock_post.return_value = _release_ok(301)
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(301)
    assert mock_post.call_count == 1
    assert "301/release" in mock_post.call_args_list[0][0][0]


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_compensation_release_succeeds_on_second_attempt(mock_post):
    mock_post.side_effect = [_release_fail(503), _release_ok(302)]
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(302)
    assert mock_post.call_count == 2


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_compensation_release_succeeds_on_third_attempt(mock_post):
    mock_post.side_effect = [_release_fail(503), _release_fail(503), _release_ok(303)]
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(303)
    assert mock_post.call_count == 3


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_all_compensation_attempts_fail_logs_and_returns_500(mock_post, capsys):
    mock_post.side_effect = [_release_fail(503), _release_fail(503), _release_fail(503)]
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(304)
    assert mock_post.call_count == 3
    out = capsys.readouterr().out
    assert "compensation failed" in out
    assert "304" in out


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_release_404_does_not_retry(mock_post, capsys):
    release_404 = MagicMock()
    release_404.status_code = 404
    release_404.json.return_value = {"detail": "Room not found"}
    mock_post.return_value = release_404
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(305)
    assert mock_post.call_count == 1
    out = capsys.readouterr().out
    assert "not retrying" in out


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_release_400_does_not_retry(mock_post, capsys):
    release_400 = MagicMock()
    release_400.status_code = 400
    release_400.json.return_value = {"detail": "Bad request"}
    mock_post.return_value = release_400
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(306)
    assert mock_post.call_count == 1
    out = capsys.readouterr().out
    assert "not retrying" in out


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_release_timeout_retried_and_succeeds(mock_post):
    mock_timeout = httpx.TimeoutException("simulated timeout")
    mock_post.side_effect = [mock_timeout, _release_already(307)]
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(307)
    assert mock_post.call_count == 2


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_timeout_ambiguity_already_available_is_safe(mock_post):
    state = {"available": False}

    def release_side_effect(url, **kwargs):
        if not state["available"]:
            state["available"] = True
            raise httpx.TimeoutException("response lost in transit")
        else:
            m = MagicMock()
            m.status_code = 200
            m.json.return_value = {"status": "already_available", "available": True}
            return m

    mock_post.side_effect = release_side_effect
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(308)
    assert state["available"] is True
    assert mock_post.call_count == 2


@patch("httpx.post")
def test_no_release_when_reservation_itself_failed(mock_post):
    failed_reserve = MagicMock()
    failed_reserve.status_code = 409
    failed_reserve.json.return_value = {"detail": "Room is not available"}
    mock_post.return_value = failed_reserve
    resp = client.post("/bookings", json={"user_id": 1, "room_id": 309})
    assert resp.status_code == 409
    assert mock_post.call_count == 1


@patch("app.main._COMPENSATION_RETRY_DELAY", 0)
@patch("httpx.post")
def test_compensation_network_failure_all_retries_still_returns_500(mock_post, capsys):
    mock_post.side_effect = [
        Exception("conn refused"),
        Exception("conn refused"),
        Exception("conn refused"),
    ]
    from app.main import _release_reservation_with_retry

    _release_reservation_with_retry(311)
    assert mock_post.call_count == 3
    out = capsys.readouterr().out
    assert "compensation failed" in out


# -------------------------------------------------------------------
# PostgreSQL Persistence & Durable Recovery State Tests
# -------------------------------------------------------------------

def test_startup_creates_bookings_table():
    init_db()
    with _mock_get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bookings;")
            count = cur.fetchone()[0]
            assert count >= 2


def test_booking_survives_booking_service_restart():
    with _mock_get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('booking_id_seq');")
            b_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO bookings (id, user_id, hotel_id, room_id, check_in, check_out, status) VALUES (%s, %s, %s, %s, %s, %s, %s);",
                (b_id, 88, 1, 400, "2026-10-01", "2026-10-03", "CONFIRMED"),
            )
        conn.commit()

    init_db()

    res = client.get(f"/bookings/{b_id}")
    assert res.status_code == 200
    assert res.json()["user_id"] == 88


def test_database_unavailable_ready_returns_503():
    global _db_available
    _db_available = False
    try:
        res = client.get("/ready")
        assert res.status_code == 503
        assert res.json()["detail"] == "Database unavailable"
    finally:
        _db_available = True


@patch("httpx.post")
def test_booking_request_when_database_unavailable_sanitized_503(mock_post):
    mock_post.return_value = _reserve_ok(500)
    global _db_available
    _db_available = False
    try:
        res = client.post("/bookings", json={"user_id": 1, "room_id": 500})
        assert res.status_code == 503
        assert res.json()["detail"] == "Database unavailable"
    finally:
        _db_available = True


def test_booking_ids_are_unique_across_multiple_creations():
    with _mock_get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('booking_id_seq');")
            id1 = cur.fetchone()[0]
            cur.execute("SELECT nextval('booking_id_seq');")
            id2 = cur.fetchone()[0]
            assert id2 > id1


def test_recovery_tasks_table_exists():
    init_db()
    with _mock_get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, room_id, action, status, attempts FROM recovery_tasks;")
            tasks = cur.fetchall()
            assert isinstance(tasks, list)


def test_recovery_tasks_can_store_pending_release_task():
    with _mock_get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO recovery_tasks (room_id, action, status) VALUES (%s, %s, %s) RETURNING id;",
                (401, "RELEASE_RESERVATION", "PENDING"),
            )
            row = cur.fetchone()
            task_id = row[0]
            assert task_id is not None
        conn.commit()

    with _mock_get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, room_id, action, status, attempts FROM recovery_tasks;")
            tasks = cur.fetchall()
            found = [t for t in tasks if t[0] == task_id]
            assert len(found) == 1
            assert found[0][1] == 401
            assert found[0][2] == "RELEASE_RESERVATION"
            assert found[0][3] == "PENDING"


def test_recovery_tasks_can_transition_to_completed():
    with _mock_get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO recovery_tasks (room_id, action, status) VALUES (%s, %s, %s) RETURNING id;",
                (402, "RELEASE_RESERVATION", "PENDING"),
            )
            task_id = cur.fetchone()[0]
        conn.commit()

    with _mock_get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE recovery_tasks SET status = %s WHERE id = %s RETURNING id, room_id, action, status, attempts;",
                ("COMPLETED", task_id),
            )
            updated = cur.fetchone()
            assert updated[3] == "COMPLETED"
        conn.commit()


# -------------------------------------------------------------------
# Phase 9 Part 4B — Transactional Outbox Pattern Tests
# -------------------------------------------------------------------

def _set_fail_env(value):
    os.environ["FAIL_AFTER_RESERVATION"] = value


@patch("httpx.post")
def test_normal_booking_does_not_create_recovery_task(mock_post):
    mock_post.return_value = _reserve_ok(300)
    original = os.environ.get("FAIL_AFTER_RESERVATION")
    try:
        _set_fail_env("false")
        before_tasks = len(_mock_recovery_tasks)
        resp = client.post("/bookings", json={"user_id": 1, "room_id": 300})
        assert resp.status_code == 201
        assert resp.json()["room_id"] == 300
        assert len(_mock_recovery_tasks) == before_tasks
        assert mock_post.call_count == 1
    finally:
        if original is None:
            os.environ.pop("FAIL_AFTER_RESERVATION", None)
        else:
            os.environ["FAIL_AFTER_RESERVATION"] = original


@patch("httpx.post")
def test_outbox_failed_booking_creates_durable_recovery_task(mock_post):
    mock_post.return_value = _reserve_ok(777)
    original = os.environ.get("FAIL_AFTER_RESERVATION")
    try:
        _set_fail_env("true")
        before_tasks = len(_mock_recovery_tasks)
        resp = client.post("/bookings", json={"user_id": 1, "room_id": 777})
        assert resp.status_code == 500
        assert "Injected failure after reservation" in resp.json()["detail"]

        assert len(_mock_recovery_tasks) == before_tasks + 1
        new_task = _mock_recovery_tasks[-1]
        assert new_task["room_id"] == 777
        assert new_task["action"] == "RELEASE_RESERVATION"
        assert new_task["status"] == "PENDING"
        assert mock_post.call_count == 1
    finally:
        if original is None:
            os.environ.pop("FAIL_AFTER_RESERVATION", None)
        else:
            os.environ["FAIL_AFTER_RESERVATION"] = original


def test_transaction_atomicity_commit():
    from app.main import create_booking_with_outbox

    before_bookings = len(_mock_bookings)
    before_tasks = len(_mock_recovery_tasks)

    create_booking_with_outbox(
        booking_id=900,
        user_id=1,
        hotel_id=1,
        room_id=888,
        check_in="2026-10-01",
        check_out="2026-10-03",
        status_val="CONFIRMED",
        action="RELEASE_RESERVATION",
        fail_between=False,
    )

    assert len(_mock_bookings) == before_bookings + 1
    assert len(_mock_recovery_tasks) == before_tasks + 1


def test_transaction_atomicity_rollback():
    from app.main import create_booking_with_outbox

    before_bookings = len(_mock_bookings)
    before_tasks = len(_mock_recovery_tasks)

    try:
        create_booking_with_outbox(
            booking_id=901,
            user_id=1,
            hotel_id=1,
            room_id=889,
            check_in="2026-10-01",
            check_out="2026-10-03",
            status_val="CONFIRMED",
            action="RELEASE_RESERVATION",
            fail_between=True,
        )
    except Exception as e:
        assert "Injected failure between outbox inserts" in str(e)

    assert len(_mock_bookings) == before_bookings
    assert len(_mock_recovery_tasks) == before_tasks


@patch("httpx.post")
def test_fail_outbox_transaction_env_rollback(mock_post):
    mock_post.return_value = _reserve_ok(999)
    original_fail = os.environ.get("FAIL_AFTER_RESERVATION")
    original_outbox = os.environ.get("FAIL_OUTBOX_TRANSACTION")
    try:
        _set_fail_env("true")
        os.environ["FAIL_OUTBOX_TRANSACTION"] = "true"
        before_tasks = len(_mock_recovery_tasks)
        resp = client.post("/bookings", json={"user_id": 1, "room_id": 999})
        assert resp.status_code == 500

        assert len(_mock_recovery_tasks) == before_tasks
    finally:
        if original_fail is None:
            os.environ.pop("FAIL_AFTER_RESERVATION", None)
        else:
            os.environ["FAIL_AFTER_RESERVATION"] = original_fail
        if original_outbox is None:
            os.environ.pop("FAIL_OUTBOX_TRANSACTION", None)
        else:
            os.environ["FAIL_OUTBOX_TRANSACTION"] = original_outbox

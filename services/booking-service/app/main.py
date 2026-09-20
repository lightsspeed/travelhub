from contextlib import asynccontextmanager
import os
import threading
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, Response, status
import httpx
import psycopg
from pydantic import BaseModel

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://travelhub_booking:bookingpass@localhost:5432/booking_db",
)


def get_db_connection():
    return psycopg.connect(DATABASE_URL, connect_timeout=2)


def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bookings (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        hotel_id INTEGER NOT NULL DEFAULT 1,
                        room_id INTEGER NOT NULL,
                        check_in TEXT NOT NULL DEFAULT '2026-10-01',
                        check_out TEXT NOT NULL DEFAULT '2026-10-03',
                        status TEXT NOT NULL
                    );
                """)
                cur.execute("CREATE SEQUENCE IF NOT EXISTS booking_id_seq START WITH 3;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS recovery_tasks (
                        id SERIAL PRIMARY KEY,
                        room_id INTEGER NOT NULL,
                        action TEXT NOT NULL,
                        status TEXT NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("SELECT COUNT(*) FROM bookings;")
                count = cur.fetchone()[0]
                if count == 0:
                    cur.execute("""
                        INSERT INTO bookings (id, user_id, hotel_id, room_id, check_in, check_out, status)
                        VALUES
                            (1, 1, 1, 1, '2026-10-01', '2026-10-03', 'CONFIRMED'),
                            (2, 2, 2, 3, '2026-11-10', '2026-11-15', 'PENDING');
                    """)
                    cur.execute("SELECT setval('booking_id_seq', 2);")
            conn.commit()
    except Exception as e:
        print(f"Booking service DB init warning: {e}")


MAX_COMPENSATION_ATTEMPTS = 3
_COMPENSATION_RETRY_DELAY = 1.0

RECOVERY_WORKER_INTERVAL_SECONDS = float(
    os.getenv("RECOVERY_WORKER_INTERVAL_SECONDS", "5")
)
recovery_worker_stop_event = threading.Event()



def _release_reservation_with_retry(room_id: int) -> tuple[str, int]:
    """Attempt to release a room reservation, retrying on transient failures.

    Returns:
        (task_status, attempts_made)
        where task_status is one of:
            - 'COMPLETED': HTTP 200 (released / already_available)
            - 'FAILED': HTTP 400 or 404 (non-retryable failure)
            - 'PENDING': HTTP 5xx, timeout, or network exception across all attempts
    """
    import time

    release_url = f"{AVAILABILITY_SERVICE_URL}/availability/{room_id}/release"
    attempts_made = 0

    for attempt in range(1, MAX_COMPENSATION_ATTEMPTS + 1):
        attempts_made += 1
        try:
            resp = httpx.post(release_url, timeout=5.0)

            if resp.status_code == 200:
                # Both "released" and "already_available" return 200 — success either way.
                return ("COMPLETED", attempts_made)

            if resp.status_code in (400, 404):
                # Non-retryable: 400 or 404. Task cannot recover automatically -> FAILED.
                print(
                    f"Booking creation failed and reservation compensation failed "
                    f"(release returned {resp.status_code} for room {room_id}, not retrying)"
                )
                return ("FAILED", attempts_made)

            # 5xx or other status — transient failure, will retry up to MAX_COMPENSATION_ATTEMPTS.
            print(
                f"Booking creation failed and reservation compensation failed "
                f"(release attempt {attempt}/{MAX_COMPENSATION_ATTEMPTS} returned "
                f"{resp.status_code} for room {room_id})"
            )

        except Exception as exc:
            print(
                f"Booking creation failed and reservation compensation failed "
                f"(release attempt {attempt}/{MAX_COMPENSATION_ATTEMPTS} raised "
                f"{exc!r} for room {room_id})"
            )

        if attempt < MAX_COMPENSATION_ATTEMPTS:
            time.sleep(_COMPENSATION_RETRY_DELAY)

    print(
        f"Booking creation failed and reservation compensation failed "
        f"(all {MAX_COMPENSATION_ATTEMPTS} release attempts exhausted for room {room_id})"
    )
    return ("PENDING", attempts_made)


def process_recovery_task(task: dict) -> str:
    """Process a single recovery task in a short database transaction."""
    task_id = task["id"]
    action = task["action"]
    room_id = task["room_id"]

    if action == "RELEASE_RESERVATION":
        task_status, attempts_made = _release_reservation_with_retry(room_id)
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    if task_status == "COMPLETED":
                        cur.execute(
                            """
                            UPDATE recovery_tasks
                            SET status = 'COMPLETED', attempts = attempts + %s
                            WHERE id = %s AND status = 'PENDING';
                            """,
                            (attempts_made, task_id),
                        )
                        print(f"recovery task {task_id} completed")
                    elif task_status == "FAILED":
                        cur.execute(
                            """
                            UPDATE recovery_tasks
                            SET status = 'FAILED', attempts = attempts + %s
                            WHERE id = %s AND status = 'PENDING';
                            """,
                            (attempts_made, task_id),
                        )
                        print(f"recovery task {task_id} failed permanently (400/404), marked FAILED")
                    else:
                        # PENDING
                        cur.execute(
                            """
                            UPDATE recovery_tasks
                            SET attempts = attempts + %s
                            WHERE id = %s AND status = 'PENDING';
                            """,
                            (attempts_made, task_id),
                        )
                        print(f"recovery task {task_id} failed, will retry")
                conn.commit()
        except Exception as exc:
            print(f"Failed to update status for recovery task {task_id}: {exc}")
        return task_status
    else:
        print(
            f"Unsupported recovery task action '{action}' for task {task_id}, marking as FAILED"
        )
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE recovery_tasks
                        SET status = 'FAILED', attempts = attempts + 1
                        WHERE id = %s AND status = 'PENDING';
                        """,
                        (task_id,),
                    )
                conn.commit()
        except Exception as exc:
            print(f"Failed to update FAILED status for recovery task {task_id}: {exc}")
        return "FAILED"



def process_recovery_tasks():
    """Fetch pending recovery tasks from PostgreSQL and process each task."""
    tasks = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, room_id, action, status, attempts
                    FROM recovery_tasks
                    WHERE status = 'PENDING'
                    ORDER BY id;
                    """
                )
                rows = cur.fetchall()
                tasks = [
                    {
                        "id": r[0],
                        "room_id": r[1],
                        "action": r[2],
                        "status": r[3],
                        "attempts": r[4],
                    }
                    for r in rows
                ]
    except Exception as exc:
        print(f"Recovery worker failed to fetch pending tasks from DB: {exc}")
        return

    for task in tasks:
        print(f"processing recovery task {task['id']}")
        process_recovery_task(task)


def recovery_worker():
    """Background recovery worker loop running periodically until stopped."""
    while not recovery_worker_stop_event.is_set():
        try:
            process_recovery_tasks()
        except Exception as exc:
            print(f"Unhandled error in recovery worker loop: {exc}")
        recovery_worker_stop_event.wait(RECOVERY_WORKER_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    recovery_worker_stop_event.clear()
    worker_thread = threading.Thread(target=recovery_worker, daemon=True)
    worker_thread.start()
    try:
        yield
    finally:
        recovery_worker_stop_event.set()
        worker_thread.join(timeout=2.0)


app = FastAPI(title="TravelHub Booking Service", lifespan=lifespan)


ALLOWED_STATUSES = {"PENDING", "CONFIRMED", "CANCELLED"}
AVAILABILITY_SERVICE_URL = os.getenv(
    "AVAILABILITY_SERVICE_URL", "http://localhost:8005"
)


class BookingCreate(BaseModel):
    user_id: int
    room_id: int
    hotel_id: Optional[int] = 1
    check_in: Optional[str] = "2026-10-01"
    check_out: Optional[str] = "2026-10-03"


class BookingStatusUpdate(BaseModel):
    status: str


class Booking(BaseModel):
    id: int
    user_id: int
    hotel_id: int
    room_id: int
    check_in: str
    check_out: str
    status: str


idempotency_store_lock = threading.Lock()
idempotency_store: dict = {}


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "booking-service"}


@app.get("/ready")
def get_ready():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ready", "service": "booking-service"}
    except Exception as e:
        print(f"Booking service database ready check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/bookings", response_model=List[Booking])
def get_bookings():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, user_id, hotel_id, room_id, check_in, check_out, status FROM bookings ORDER BY id;"
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "user_id": r[1],
                        "hotel_id": r[2],
                        "room_id": r[3],
                        "check_in": r[4],
                        "check_out": r[5],
                        "status": r[6],
                    }
                    for r in rows
                ]
    except Exception as e:
        print(f"Get bookings DB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/bookings/{booking_id}", response_model=Booking)
def get_booking(booking_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, user_id, hotel_id, room_id, check_in, check_out, status FROM bookings WHERE id = %s;",
                    (booking_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Booking not found")
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "hotel_id": row[2],
                    "room_id": row[3],
                    "check_in": row[4],
                    "check_out": row[5],
                    "status": row[6],
                }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get booking DB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


MAX_COMPENSATION_ATTEMPTS = 3
_COMPENSATION_RETRY_DELAY = 0.1  # seconds between attempts


@app.post("/bookings", response_model=Booking, status_code=status.HTTP_201_CREATED)

def create_booking(
    payload: BookingCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    # Check / claim idempotency key if provided
    if idempotency_key:
        event_to_wait = None
        with idempotency_store_lock:
            if idempotency_key in idempotency_store:
                entry = idempotency_store[idempotency_key]
                if entry["status"] in ("pending", "completed"):
                    current_payload = payload.model_dump()
                    if entry["payload"] != current_payload:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Idempotency key already used for a different request",
                        )
                    if entry["status"] == "completed":
                        return entry["booking"]
                    elif entry["status"] == "pending":
                        event_to_wait = entry["event"]

            if event_to_wait is None:
                # First request claims the key
                event = threading.Event()
                idempotency_store[idempotency_key] = {
                    "payload": payload.model_dump(),
                    "status": "pending",
                    "event": event,
                    "booking": None,
                    "error": None,
                }

        # If a first request is currently in-flight, wait for it
        if event_to_wait is not None:
            event_to_wait.wait(timeout=10.0)
            with idempotency_store_lock:
                entry = idempotency_store.get(idempotency_key)
                if entry and entry["status"] == "completed":
                    return entry["booking"]
                elif entry and entry["error"] is not None:
                    raise entry["error"]
                else:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Availability service unavailable",
                    )

    # Allocate booking ID from PostgreSQL sequence
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nextval('booking_id_seq');")
                booking_id = cur.fetchone()[0]
    except Exception as exc:
        print(f"Failed to allocate booking ID from sequence: {exc}")
        err = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
        if idempotency_key:
            with idempotency_store_lock:
                entry = idempotency_store.get(idempotency_key)
                if entry and entry["status"] == "pending":
                    entry["status"] = "failed"
                    entry["error"] = err
                    entry["event"].set()
        raise err

    # Call availability-service to reserve the room
    reserve_url = (
        f"{AVAILABILITY_SERVICE_URL}/availability/{payload.room_id}/reserve"
    )
    err_to_raise = None
    try:
        response = httpx.post(
            reserve_url,
            json={"booking_id": booking_id},
            timeout=5.0,
        )
        if response.status_code == 404:
            err_to_raise = HTTPException(status_code=404, detail="Room not found")
        elif response.status_code == 409:
            err_to_raise = HTTPException(
                status_code=409, detail="Room is not available"
            )
        elif response.status_code not in (200, 201):
            err_to_raise = HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Availability service unavailable",
            )
    except HTTPException as exc:
        err_to_raise = exc
    except Exception:
        err_to_raise = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Availability service unavailable",
        )

    # Check failure-injection environment variables
    fail_after_reservation = (
        os.getenv("FAIL_AFTER_RESERVATION", "false").lower() in ("true", "1")
    )
    fail_outbox_transaction = (
        os.getenv("FAIL_OUTBOX_TRANSACTION", "false").lower() in ("true", "1")
    )
    reservation_succeeded = err_to_raise is None

    if reservation_succeeded and fail_after_reservation:
        # Failure injected after reservation: record durable recovery task in PostgreSQL transaction
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO recovery_tasks (room_id, action, status, attempts)
                        VALUES (%s, %s, %s, %s);
                        """,
                        (payload.room_id, "RELEASE_RESERVATION", "PENDING", 0),
                    )
                    if fail_outbox_transaction:
                        raise Exception("Injected failure during outbox transaction")
                conn.commit()
        except Exception as exc:
            print(f"Outbox recovery task insertion failed or rolled back: {exc}")

        err_to_raise = HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Injected failure after reservation",
        )

    # Handle failure case
    if err_to_raise is not None:
        if idempotency_key:
            with idempotency_store_lock:
                entry = idempotency_store.get(idempotency_key)
                if entry and entry["status"] == "pending":
                    entry["status"] = "failed"
                    entry["error"] = err_to_raise
                    entry["event"].set()
        raise err_to_raise

    # Store booking into PostgreSQL for normal successful booking
    hotel_id = payload.hotel_id if payload.hotel_id is not None else 1
    check_in = payload.check_in if payload.check_in is not None else "2026-10-01"
    check_out = payload.check_out if payload.check_out is not None else "2026-10-03"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bookings (id, user_id, hotel_id, room_id, check_in, check_out, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        booking_id,
                        payload.user_id,
                        hotel_id,
                        payload.room_id,
                        check_in,
                        check_out,
                        "CONFIRMED",
                    ),
                )
                if fail_outbox_transaction:
                    raise Exception("Injected failure during outbox transaction")
            conn.commit()
    except Exception as exc:
        print(f"Failed to insert booking into database: {exc}")
        err = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
        if idempotency_key:
            with idempotency_store_lock:
                entry = idempotency_store.get(idempotency_key)
                if entry and entry["status"] == "pending":
                    entry["status"] = "failed"
                    entry["error"] = err
                    entry["event"].set()
        raise err

    new_booking = {
        "id": booking_id,
        "user_id": payload.user_id,
        "hotel_id": hotel_id,
        "room_id": payload.room_id,
        "check_in": check_in,
        "check_out": check_out,
        "status": "CONFIRMED",
    }

    if idempotency_key:
        with idempotency_store_lock:
            entry = idempotency_store.get(idempotency_key)
            if entry:
                entry["status"] = "completed"
                entry["booking"] = new_booking
                entry["event"].set()

    return new_booking


def create_booking_with_outbox(
    booking_id: int,
    user_id: int,
    hotel_id: int,
    room_id: int,
    check_in: str,
    check_out: str,
    status_val: str,
    action: str = "RELEASE_RESERVATION",
    fail_between: bool = False,
):
    """Atomic transaction helper that inserts both booking and recovery_task in ONE transaction."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bookings (id, user_id, hotel_id, room_id, check_in, check_out, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (booking_id, user_id, hotel_id, room_id, check_in, check_out, status_val),
            )
            if fail_between or os.getenv("FAIL_OUTBOX_TRANSACTION", "false").lower() in ("true", "1"):
                raise Exception("Injected failure between outbox inserts")
            cur.execute(
                """
                INSERT INTO recovery_tasks (room_id, action, status, attempts)
                VALUES (%s, %s, %s, %s);
                """,
                (room_id, action, "PENDING", 0),
            )
        conn.commit()


@app.patch("/bookings/{booking_id}/status", response_model=Booking)
def update_booking_status(booking_id: int, payload: BookingStatusUpdate):

    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Allowed statuses: {sorted(list(ALLOWED_STATUSES))}",
        )
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE bookings SET status = %s WHERE id = %s RETURNING id, user_id, hotel_id, room_id, check_in, check_out, status;",
                    (payload.status, booking_id),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Booking not found")
            conn.commit()
            return {
                "id": row[0],
                "user_id": row[1],
                "hotel_id": row[2],
                "room_id": row[3],
                "check_in": row[4],
                "check_out": row[5],
                "status": row[6],
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update booking status DB error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8006"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

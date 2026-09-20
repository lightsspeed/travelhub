import os
import threading
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, Response, status
import httpx
from pydantic import BaseModel

app = FastAPI(title="TravelHub Booking Service")

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


# In-memory bookings store
bookings_db: List[dict] = [
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

next_booking_id = 3
idempotency_store_lock = threading.Lock()
idempotency_store: dict = {}


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "booking-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "booking-service"}


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
    return bookings_db


@app.get("/bookings/{booking_id}", response_model=Booking)
def get_booking(booking_id: int):
    for b in bookings_db:
        if b["id"] == booking_id:
            return b
    raise HTTPException(status_code=404, detail="Booking not found")


@app.post("/bookings", response_model=Booking, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    global next_booking_id

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

    # Allocate booking ID BEFORE I/O call
    with idempotency_store_lock:
        booking_id = next_booking_id
        next_booking_id += 1

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

    # Handle success case
    new_booking = {
        "id": booking_id,
        "user_id": payload.user_id,
        "hotel_id": payload.hotel_id if payload.hotel_id is not None else 1,
        "room_id": payload.room_id,
        "check_in": (
            payload.check_in if payload.check_in is not None else "2026-10-01"
        ),
        "check_out": (
            payload.check_out if payload.check_out is not None else "2026-10-03"
        ),
        "status": "CONFIRMED",
    }
    bookings_db.append(new_booking)

    if idempotency_key:
        with idempotency_store_lock:
            entry = idempotency_store.get(idempotency_key)
            if entry:
                entry["status"] = "completed"
                entry["booking"] = new_booking
                entry["event"].set()

    return new_booking


@app.patch("/bookings/{booking_id}/status", response_model=Booking)
def update_booking_status(booking_id: int, payload: BookingStatusUpdate):
    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Allowed statuses: {sorted(list(ALLOWED_STATUSES))}",
        )

    for b in bookings_db:
        if b["id"] == booking_id:
            b["status"] = payload.status
            return b

    raise HTTPException(status_code=404, detail="Booking not found")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8006"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

import os
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI(title="TravelHub Booking Service")

ALLOWED_STATUSES = {"PENDING", "CONFIRMED", "CANCELLED"}


class BookingCreate(BaseModel):
    user_id: int
    hotel_id: int
    room_id: int
    check_in: str
    check_out: str


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
def create_booking(payload: BookingCreate):
    global next_booking_id
    new_booking = {
        "id": next_booking_id,
        "user_id": payload.user_id,
        "hotel_id": payload.hotel_id,
        "room_id": payload.room_id,
        "check_in": payload.check_in,
        "check_out": payload.check_out,
        "status": "PENDING",
    }
    next_booking_id += 1
    bookings_db.append(new_booking)
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

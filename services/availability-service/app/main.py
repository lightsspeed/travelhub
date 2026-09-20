import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI(title="TravelHub Availability Service")


class AvailabilityRecord(BaseModel):
    room_id: int
    hotel_id: int
    available: bool = True


# In-memory availability store
availability_db: List[dict] = [
    {"room_id": 1, "hotel_id": 1, "available": True},
    {"room_id": 2, "hotel_id": 1, "available": True},
    {"room_id": 3, "hotel_id": 2, "available": False},
    {"room_id": 4, "hotel_id": 2, "available": True},
    {"room_id": 5, "hotel_id": 3, "available": True},
    {"room_id": 6, "hotel_id": 4, "available": False},
]


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "availability-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "availability-service"}


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/availability", response_model=List[AvailabilityRecord])
def get_availability(
    hotel_id: Optional[int] = None, room_id: Optional[int] = None
):
    results = availability_db
    if hotel_id is not None:
        results = [a for a in results if a["hotel_id"] == hotel_id]
    if room_id is not None:
        results = [a for a in results if a["room_id"] == room_id]
    return results


@app.get("/availability/{room_id}", response_model=AvailabilityRecord)
def get_availability_by_room(room_id: int):
    for rec in availability_db:
        if rec["room_id"] == room_id:
            return rec
    raise HTTPException(status_code=404, detail="Availability record not found")


@app.post(
    "/availability",
    response_model=AvailabilityRecord,
    status_code=status.HTTP_200_OK,
)
def create_or_update_availability(payload: AvailabilityRecord):
    # Check if record already exists for room_id
    for rec in availability_db:
        if rec["room_id"] == payload.room_id:
            rec["hotel_id"] = payload.hotel_id
            rec["available"] = payload.available
            return rec

    new_rec = {
        "room_id": payload.room_id,
        "hotel_id": payload.hotel_id,
        "available": payload.available,
    }
    availability_db.append(new_rec)
    return new_rec


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8005"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

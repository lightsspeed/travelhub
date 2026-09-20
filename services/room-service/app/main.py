import os
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel
import httpx

app = FastAPI(title="TravelHub Room Service")

# Hotel service base URL — overridden via environment variable in Kubernetes.
# Default points to local development port.
HOTEL_SERVICE_URL = os.getenv("HOTEL_SERVICE_URL", "http://localhost:8002")


class RoomCreate(BaseModel):
    hotel_id: int
    room_type: str
    capacity: int
    price_per_night: float
    currency: str = "USD"
    available: bool = True


class Room(BaseModel):
    id: int
    hotel_id: int
    room_type: str
    capacity: int
    price_per_night: float
    currency: str
    available: bool


# In-memory room store
rooms_db: List[dict] = [
    {
        "id": 1,
        "hotel_id": 1,
        "room_type": "Deluxe Sea View Suite",
        "capacity": 2,
        "price_per_night": 250.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 2,
        "hotel_id": 1,
        "room_type": "Superior City View Room",
        "capacity": 2,
        "price_per_night": 150.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 3,
        "hotel_id": 2,
        "room_type": "Beachfront Villa",
        "capacity": 4,
        "price_per_night": 320.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 4,
        "hotel_id": 2,
        "room_type": "Garden Cottage",
        "capacity": 2,
        "price_per_night": 120.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 5,
        "hotel_id": 3,
        "room_type": "Skyline Luxury Suite",
        "capacity": 3,
        "price_per_night": 450.0,
        "currency": "USD",
        "available": True,
    },
    {
        "id": 6,
        "hotel_id": 4,
        "room_type": "Marina Bay View Room",
        "capacity": 2,
        "price_per_night": 280.0,
        "currency": "USD",
        "available": True,
    },
]

next_room_id = 7


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "room-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "room-service"}


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/rooms", response_model=List[Room])
def get_rooms():
    return rooms_db


@app.get("/rooms/{room_id}", response_model=Room)
def get_room(room_id: int):
    for room in rooms_db:
        if room["id"] == room_id:
            return room
    raise HTTPException(status_code=404, detail="Room not found")


@app.get("/rooms/{room_id}/hotel")
def get_room_with_hotel(room_id: int):
    """Return room details combined with hotel details fetched from hotel-service."""
    # Step 1: Find the room locally.
    room = None
    for r in rooms_db:
        if r["id"] == room_id:
            room = r
            break

    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    # Step 2: Call hotel-service for the hotel details.
    hotel_url = f"{HOTEL_SERVICE_URL}/hotels/{room['hotel_id']}"
    try:
        response = httpx.get(hotel_url, timeout=3.0)
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Hotel service unavailable")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Hotel service unavailable")

    # Step 3: Handle upstream response codes.
    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Hotel {room['hotel_id']} not found in hotel-service",
        )
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Hotel service unavailable")

    hotel = response.json()

    return {"room": room, "hotel": hotel}


@app.get("/hotels/{hotel_id}/rooms", response_model=List[Room])
def get_rooms_by_hotel(hotel_id: int):
    hotel_rooms = [room for room in rooms_db if room["hotel_id"] == hotel_id]
    return hotel_rooms


@app.post("/rooms", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate):
    global next_room_id
    new_room = {
        "id": next_room_id,
        "hotel_id": payload.hotel_id,
        "room_type": payload.room_type,
        "capacity": payload.capacity,
        "price_per_night": payload.price_per_night,
        "currency": payload.currency,
        "available": payload.available,
    }
    next_room_id += 1
    rooms_db.append(new_room)
    return new_room


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

import os
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI(title="TravelHub Hotel Service")


class HotelCreate(BaseModel):
    name: str
    city: str
    country: str
    description: str
    rating: float


class Hotel(BaseModel):
    id: int
    name: str
    city: str
    country: str
    description: str
    rating: float


# In-memory hotel store
hotels_db: List[dict] = [
    {
        "id": 1,
        "name": "The Grand Mumbai",
        "city": "Mumbai",
        "country": "India",
        "description": "Luxury hotel near Marine Drive with breathtaking ocean views.",
        "rating": 4.8,
    },
    {
        "id": 2,
        "name": "Goa Beachfront Resort",
        "city": "Goa",
        "country": "India",
        "description": "Tranquil resort with private beach access and Portuguese architecture.",
        "rating": 4.6,
    },
    {
        "id": 3,
        "name": "Dubai Oasis Hotel",
        "city": "Dubai",
        "country": "UAE",
        "description": "Iconic skyline views with world-class dining and luxury amenities.",
        "rating": 4.9,
    },
    {
        "id": 4,
        "name": "Marina Bay Vista",
        "city": "Singapore",
        "country": "Singapore",
        "description": "Contemporary waterfront hotel overlooking Marina Bay.",
        "rating": 4.7,
    },
]

next_hotel_id = 5


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "hotel-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "hotel-service"}


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/hotels", response_model=List[Hotel])
def get_hotels():
    return hotels_db


@app.get("/hotels/{hotel_id}", response_model=Hotel)
def get_hotel(hotel_id: int):
    for hotel in hotels_db:
        if hotel["id"] == hotel_id:
            return hotel
    raise HTTPException(status_code=404, detail="Hotel not found")


@app.post("/hotels", response_model=Hotel, status_code=status.HTTP_201_CREATED)
def create_hotel(payload: HotelCreate):
    global next_hotel_id
    new_hotel = {
        "id": next_hotel_id,
        "name": payload.name,
        "city": payload.city,
        "country": payload.country,
        "description": payload.description,
        "rating": payload.rating,
    }
    next_hotel_id += 1
    hotels_db.append(new_hotel)
    return new_hotel


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

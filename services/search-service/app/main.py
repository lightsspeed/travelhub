import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

app = FastAPI(title="TravelHub Search Service")


class HotelSearchResult(BaseModel):
    id: int
    name: str
    city: str
    country: str
    rating: float


# Sample in-memory search database
search_db: List[dict] = [
    {
        "id": 1,
        "name": "The Grand Mumbai",
        "city": "Mumbai",
        "country": "India",
        "rating": 4.8,
    },
    {
        "id": 2,
        "name": "Goa Beach Resort",
        "city": "Goa",
        "country": "India",
        "rating": 4.5,
    },
    {
        "id": 3,
        "name": "Tokyo Skyline Hotel",
        "city": "Tokyo",
        "country": "Japan",
        "rating": 4.7,
    },
    {
        "id": 4,
        "name": "Paris Central Hotel",
        "city": "Paris",
        "country": "France",
        "rating": 4.6,
    },
]


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "search-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "search-service"}


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/search", response_model=List[HotelSearchResult])
def search_hotels(city: Optional[str] = None, country: Optional[str] = None):
    results = search_db
    if city:
        results = [h for h in results if h["city"].lower() == city.lower()]
    if country:
        results = [h for h in results if h["country"].lower() == country.lower()]
    return results


@app.get("/search/{hotel_id}", response_model=HotelSearchResult)
def get_search_hotel(hotel_id: int):
    for hotel in search_db:
        if hotel["id"] == hotel_id:
            return hotel
    raise HTTPException(status_code=404, detail="Hotel not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8004"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

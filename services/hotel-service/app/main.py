from contextlib import asynccontextmanager
import os
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel
import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://travelhub_hotel:hotelpass@localhost:5432/hotel_db",
)


def get_db_connection():
    return psycopg.connect(DATABASE_URL, connect_timeout=2)


def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS hotels (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        city TEXT NOT NULL,
                        country TEXT NOT NULL,
                        description TEXT NOT NULL,
                        rating REAL NOT NULL
                    );
                """)
                cur.execute("SELECT COUNT(*) FROM hotels;")
                count = cur.fetchone()[0]
                if count == 0:
                    seed_hotels = [
                        (
                            1,
                            "The Grand Mumbai",
                            "Mumbai",
                            "India",
                            "Luxury hotel near Marine Drive with breathtaking ocean views.",
                            4.8,
                        ),
                        (
                            2,
                            "Goa Beachfront Resort",
                            "Goa",
                            "India",
                            "Tranquil resort with private beach access and Portuguese architecture.",
                            4.6,
                        ),
                        (
                            3,
                            "Dubai Oasis Hotel",
                            "Dubai",
                            "UAE",
                            "Iconic skyline views with world-class dining and luxury amenities.",
                            4.9,
                        ),
                        (
                            4,
                            "Marina Bay Vista",
                            "Singapore",
                            "Singapore",
                            "Contemporary waterfront hotel overlooking Marina Bay.",
                            4.7,
                        ),
                    ]
                    for h in seed_hotels:
                        cur.execute(
                            "INSERT INTO hotels (id, name, city, country, description, rating) VALUES (%s, %s, %s, %s, %s, %s)",
                            h,
                        )
            conn.commit()
    except Exception as e:
        print(f"Hotel service DB init warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="TravelHub Hotel Service", lifespan=lifespan)


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


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "hotel-service"}


@app.get("/ready")
def get_ready():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ready", "service": "hotel-service"}
    except Exception as e:
        print(f"Hotel service database ready check failed: {e}")
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


@app.get("/hotels", response_model=List[Hotel])
def get_hotels():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, city, country, description, rating FROM hotels ORDER BY id;"
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "name": r[1],
                        "city": r[2],
                        "country": r[3],
                        "description": r[4],
                        "rating": r[5],
                    }
                    for r in rows
                ]
    except Exception as e:
        print(f"Hotel service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/hotels/{hotel_id}", response_model=Hotel)
def get_hotel(hotel_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, city, country, description, rating FROM hotels WHERE id = %s;",
                    (hotel_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Hotel not found")
                return {
                    "id": row[0],
                    "name": row[1],
                    "city": row[2],
                    "country": row[3],
                    "description": row[4],
                    "rating": row[5],
                }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Hotel service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.post("/hotels", response_model=Hotel, status_code=status.HTTP_201_CREATED)
def create_hotel(payload: HotelCreate):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM hotels;")
                new_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO hotels (id, name, city, country, description, rating) VALUES (%s, %s, %s, %s, %s, %s);",
                    (
                        new_id,
                        payload.name,
                        payload.city,
                        payload.country,
                        payload.description,
                        payload.rating,
                    ),
                )
            conn.commit()
            return {
                "id": new_id,
                "name": payload.name,
                "city": payload.city,
                "country": payload.country,
                "description": payload.description,
                "rating": payload.rating,
            }
    except Exception as e:
        print(f"Hotel service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

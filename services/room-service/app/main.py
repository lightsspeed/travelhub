from contextlib import asynccontextmanager
import os
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel
import httpx
import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://travelhub_room:roompass@localhost:5432/room_db",
)

# Hotel service base URL — overridden via environment variable in Kubernetes/Docker.
HOTEL_SERVICE_URL = os.getenv("HOTEL_SERVICE_URL", "http://localhost:8002")


def get_db_connection():
    return psycopg.connect(DATABASE_URL, connect_timeout=2)


def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS rooms (
                        id INTEGER PRIMARY KEY,
                        hotel_id INTEGER NOT NULL,
                        room_type TEXT NOT NULL,
                        capacity INTEGER NOT NULL,
                        price_per_night REAL NOT NULL,
                        currency TEXT DEFAULT 'USD',
                        available BOOLEAN DEFAULT TRUE
                    );
                """)
                cur.execute("SELECT COUNT(*) FROM rooms;")
                count = cur.fetchone()[0]
                if count == 0:
                    seed_rooms = [
                        (1, 1, "Deluxe Sea View Suite", 2, 250.0, "USD", True),
                        (2, 1, "Superior City View Room", 2, 150.0, "USD", True),
                        (3, 2, "Beachfront Villa", 4, 320.0, "USD", True),
                        (4, 2, "Garden Cottage", 2, 120.0, "USD", True),
                        (5, 3, "Skyline Luxury Suite", 3, 450.0, "USD", True),
                        (6, 4, "Marina Bay View Room", 2, 280.0, "USD", True),
                    ]
                    for r in seed_rooms:
                        cur.execute(
                            "INSERT INTO rooms (id, hotel_id, room_type, capacity, price_per_night, currency, available) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            r,
                        )
            conn.commit()
    except Exception as e:
        print(f"Room service DB init warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="TravelHub Room Service", lifespan=lifespan)


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


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "room-service"}


@app.get("/ready")
def get_ready():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ready", "service": "room-service"}
    except Exception as e:
        print(f"Room service database ready check failed: {e}")
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


@app.get("/rooms", response_model=List[Room])
def get_rooms():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, hotel_id, room_type, capacity, price_per_night, currency, available FROM rooms ORDER BY id;"
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "hotel_id": r[1],
                        "room_type": r[2],
                        "capacity": r[3],
                        "price_per_night": r[4],
                        "currency": r[5],
                        "available": bool(r[6]),
                    }
                    for r in rows
                ]
    except Exception as e:
        print(f"Room service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/rooms/{room_id}", response_model=Room)
def get_room(room_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, hotel_id, room_type, capacity, price_per_night, currency, available FROM rooms WHERE id = %s;",
                    (room_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Room not found")
                return {
                    "id": row[0],
                    "hotel_id": row[1],
                    "room_type": row[2],
                    "capacity": row[3],
                    "price_per_night": row[4],
                    "currency": row[5],
                    "available": bool(row[6]),
                }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Room service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/rooms/{room_id}/hotel")
def get_room_with_hotel(room_id: int):
    """Return room details combined with hotel details fetched from hotel-service."""
    room = None
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, hotel_id, room_type, capacity, price_per_night, currency, available FROM rooms WHERE id = %s;",
                    (room_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Room not found")
                room = {
                    "id": row[0],
                    "hotel_id": row[1],
                    "room_type": row[2],
                    "capacity": row[3],
                    "price_per_night": row[4],
                    "currency": row[5],
                    "available": bool(row[6]),
                }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Room service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )

    # Step 2: Call hotel-service for the hotel details via HTTP
    hotel_url = f"{HOTEL_SERVICE_URL}/hotels/{room['hotel_id']}"
    try:
        response = httpx.get(hotel_url, timeout=3.0)
    except (httpx.TimeoutException, httpx.RequestError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hotel service unavailable",
        )

    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Hotel {room['hotel_id']} not found in hotel-service",
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hotel service unavailable",
        )

    hotel = response.json()
    return {"room": room, "hotel": hotel}


@app.get("/hotels/{hotel_id}/rooms", response_model=List[Room])
def get_rooms_by_hotel(hotel_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, hotel_id, room_type, capacity, price_per_night, currency, available FROM rooms WHERE hotel_id = %s ORDER BY id;",
                    (hotel_id,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "hotel_id": r[1],
                        "room_type": r[2],
                        "capacity": r[3],
                        "price_per_night": r[4],
                        "currency": r[5],
                        "available": bool(r[6]),
                    }
                    for r in rows
                ]
    except Exception as e:
        print(f"Room service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.post("/rooms", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM rooms;")
                new_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO rooms (id, hotel_id, room_type, capacity, price_per_night, currency, available) VALUES (%s, %s, %s, %s, %s, %s, %s);",
                    (
                        new_id,
                        payload.hotel_id,
                        payload.room_type,
                        payload.capacity,
                        payload.price_per_night,
                        payload.currency,
                        payload.available,
                    ),
                )
            conn.commit()
            return {
                "id": new_id,
                "hotel_id": payload.hotel_id,
                "room_type": payload.room_type,
                "capacity": payload.capacity,
                "price_per_night": payload.price_per_night,
                "currency": payload.currency,
                "available": payload.available,
            }
    except Exception as e:
        print(f"Room service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

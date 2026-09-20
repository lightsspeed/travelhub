from contextlib import asynccontextmanager
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel
import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://travelhub_availability:availabilitypass@localhost:5432/availability_db",
)


def get_db_connection():
    return psycopg.connect(DATABASE_URL, connect_timeout=2)


def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS availability (
                        room_id INTEGER PRIMARY KEY,
                        available BOOLEAN NOT NULL
                    );
                """)
                cur.execute("SELECT COUNT(*) FROM availability;")
                count = cur.fetchone()[0]
                if count == 0:
                    seed_rooms = [(i, True) for i in range(1, 7)]
                    for room in seed_rooms:
                        cur.execute(
                            "INSERT INTO availability (room_id, available) VALUES (%s, %s);",
                            room,
                        )
            conn.commit()
    except Exception as e:
        print(f"Availability service DB init warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="TravelHub Availability Service", lifespan=lifespan)


class AvailabilityRecord(BaseModel):
    room_id: int
    available: bool = True


class ReserveRequest(BaseModel):
    booking_id: Optional[int] = None


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "availability-service"}


@app.get("/ready")
def get_ready():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ready", "service": "availability-service"}
    except Exception as e:
        print(f"Availability service database ready check failed: {e}")
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


@app.get("/availability", response_model=List[AvailabilityRecord])
def get_availability(
    hotel_id: Optional[int] = None, room_id: Optional[int] = None
):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if room_id is not None:
                    cur.execute(
                        "SELECT room_id, available FROM availability WHERE room_id = %s;",
                        (room_id,),
                    )
                else:
                    cur.execute(
                        "SELECT room_id, available FROM availability ORDER BY room_id;"
                    )
                rows = cur.fetchall()
                return [{"room_id": r[0], "available": r[1]} for r in rows]
    except Exception as e:
        print(f"Availability service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/availability/{room_id}", response_model=AvailabilityRecord)
def get_availability_by_room(room_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT room_id, available FROM availability WHERE room_id = %s;",
                    (room_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(
                        status_code=404, detail="Availability record not found"
                    )
                return {"room_id": row[0], "available": row[1]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Availability service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.post(
    "/availability",
    response_model=AvailabilityRecord,
    status_code=status.HTTP_200_OK,
)
def create_or_update_availability(payload: AvailabilityRecord):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO availability (room_id, available)
                    VALUES (%s, %s)
                    ON CONFLICT (room_id) DO UPDATE SET available = EXCLUDED.available;
                    """,
                    (payload.room_id, payload.available),
                )
            conn.commit()
            return {"room_id": payload.room_id, "available": payload.available}
    except Exception as e:
        print(f"Availability service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.post("/availability/{room_id}/reserve")
def reserve_room(room_id: int, payload: Optional[ReserveRequest] = None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Atomic conditional UPDATE
                cur.execute(
                    """
                    UPDATE availability
                    SET available = false
                    WHERE room_id = %s AND available = true;
                    """,
                    (room_id,),
                )
                if cur.rowcount == 1:
                    conn.commit()
                    booking_id = payload.booking_id if payload else None
                    return {
                        "room_id": room_id,
                        "available": False,
                        "booking_id": booking_id,
                        "status": "reserved",
                    }

                # If rowcount == 0, query database to distinguish 404 (nonexistent) vs 409 (already unavailable)
                cur.execute(
                    "SELECT room_id, available FROM availability WHERE room_id = %s;",
                    (room_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="Room not found")
                else:
                    raise HTTPException(
                        status_code=409, detail="Room is not available"
                    )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Availability service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8005"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

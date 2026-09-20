from contextlib import asynccontextmanager
import os
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel
import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://travelhub_user:userpass@localhost:5432/user_db",
)


def get_db_connection():
    return psycopg.connect(DATABASE_URL, connect_timeout=2)


def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL
                    );
                """)
                cur.execute("SELECT COUNT(*) FROM users;")
                count = cur.fetchone()[0]
                if count == 0:
                    seed_users = [
                        (1, "Akhil", "akhil@example.com"),
                        (2, "Priya Sharma", "priya@example.com"),
                        (3, "John Doe", "john@example.com"),
                    ]
                    for u in seed_users:
                        cur.execute(
                            "INSERT INTO users (id, name, email) VALUES (%s, %s, %s)",
                            u,
                        )
            conn.commit()
    except Exception as e:
        print(f"User service DB init warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="TravelHub User Service", lifespan=lifespan)


class UserCreate(BaseModel):
    name: str
    email: str


class User(BaseModel):
    id: int
    name: str
    email: str


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "user-service"}


@app.get("/ready")
def get_ready():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ready", "service": "user-service"}
    except Exception as e:
        print(f"User service database ready check failed: {e}")
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


@app.get("/users", response_model=List[User])
def get_users():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, email FROM users ORDER BY id;")
                rows = cur.fetchall()
                return [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]
    except Exception as e:
        print(f"User service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, email FROM users WHERE id = %s;",
                    (user_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail="User not found")
                return {"id": row[0], "name": row[1], "email": row[2]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"User service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM users;")
                new_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO users (id, name, email) VALUES (%s, %s, %s);",
                    (new_id, payload.name, payload.email),
                )
            conn.commit()
            return {"id": new_id, "name": payload.name, "email": payload.email}
    except Exception as e:
        print(f"User service database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

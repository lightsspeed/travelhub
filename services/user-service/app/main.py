import os
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI(title="TravelHub User Service")


class UserCreate(BaseModel):
    name: str
    email: str


class User(BaseModel):
    id: int
    name: str
    email: str


# In-memory user store
users_db: List[dict] = [
    {"id": 1, "name": "Akhil", "email": "akhil@example.com"},
    {"id": 2, "name": "Priya Sharma", "email": "priya@example.com"},
    {"id": 3, "name": "John Doe", "email": "john@example.com"},
]

# Track next user ID
next_user_id = 4


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "user-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "user-service"}


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
    return users_db


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    for user in users_db:
        if user["id"] == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")


@app.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate):
    global next_user_id
    new_user = {
        "id": next_user_id,
        "name": payload.name,
        "email": payload.email,
    }
    next_user_id += 1
    users_db.append(new_user)
    return new_user


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

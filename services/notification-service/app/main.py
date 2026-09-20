import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI(title="TravelHub Notification Service")

ALLOWED_STATUSES = {"PENDING", "SENT", "FAILED"}


class NotificationCreate(BaseModel):
    user_id: int
    type: str
    message: str


class NotificationStatusUpdate(BaseModel):
    status: str


class Notification(BaseModel):
    id: int
    user_id: int
    type: str
    message: str
    status: str


# In-memory notifications store
notifications_db: List[dict] = [
    {
        "id": 1,
        "user_id": 1,
        "type": "BOOKING_CONFIRMED",
        "message": "Your hotel booking #1 has been confirmed.",
        "status": "SENT",
    },
    {
        "id": 2,
        "user_id": 2,
        "type": "PAYMENT_RECEIVED",
        "message": "Payment for booking #2 received successfully.",
        "status": "PENDING",
    },
]

next_notification_id = 3


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "notification-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "notification-service"}


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/notifications", response_model=List[Notification])
def get_notifications(user_id: Optional[int] = None):
    results = notifications_db
    if user_id is not None:
        results = [n for n in results if n["user_id"] == user_id]
    return results


@app.get("/notifications/{notification_id}", response_model=Notification)
def get_notification(notification_id: int):
    for n in notifications_db:
        if n["id"] == notification_id:
            return n
    raise HTTPException(status_code=404, detail="Notification not found")


@app.post(
    "/notifications",
    response_model=Notification,
    status_code=status.HTTP_201_CREATED,
)
def create_notification(payload: NotificationCreate):
    global next_notification_id
    new_notif = {
        "id": next_notification_id,
        "user_id": payload.user_id,
        "type": payload.type,
        "message": payload.message,
        "status": "PENDING",
    }
    next_notification_id += 1
    notifications_db.append(new_notif)
    return new_notif


@app.patch("/notifications/{notification_id}/status", response_model=Notification)
def update_notification_status(
    notification_id: int, payload: NotificationStatusUpdate
):
    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{payload.status}'. Allowed statuses: {sorted(list(ALLOWED_STATUSES))}",
        )

    for n in notifications_db:
        if n["id"] == notification_id:
            n["status"] = payload.status
            return n

    raise HTTPException(status_code=404, detail="Notification not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8009"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

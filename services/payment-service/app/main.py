import os
from typing import List
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI(title="TravelHub Payment Service")


class PaymentCreate(BaseModel):
    booking_id: int
    amount: float
    currency: str = "USD"


class Payment(BaseModel):
    id: int
    booking_id: int
    amount: float
    currency: str
    status: str


# In-memory payments store
payments_db: List[dict] = [
    {
        "id": 1,
        "booking_id": 1,
        "amount": 500.0,
        "currency": "USD",
        "status": "SUCCESS",
    },
    {
        "id": 2,
        "booking_id": 2,
        "amount": 300.0,
        "currency": "USD",
        "status": "SUCCESS",
    },
]

next_payment_id = 3


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "payment-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "payment-service"}


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/payments", response_model=List[Payment])
def get_payments():
    return payments_db


@app.get("/payments/{payment_id}", response_model=Payment)
def get_payment(payment_id: int):
    for p in payments_db:
        if p["id"] == payment_id:
            return p
    raise HTTPException(status_code=404, detail="Payment not found")


@app.post("/payments", response_model=Payment, status_code=status.HTTP_201_CREATED)
def create_payment(payload: PaymentCreate):
    if payload.amount <= 0:
        raise HTTPException(
            status_code=400, detail="Amount must be greater than zero"
        )

    global next_payment_id
    new_payment = {
        "id": next_payment_id,
        "booking_id": payload.booking_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "status": "SUCCESS",
    }
    next_payment_id += 1
    payments_db.append(new_payment)
    return new_payment


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8007"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

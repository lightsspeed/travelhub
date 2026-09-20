import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel

app = FastAPI(title="TravelHub Review Service")


class ReviewCreate(BaseModel):
    user_id: int
    hotel_id: int
    rating: int
    comment: str


class Review(BaseModel):
    id: int
    user_id: int
    hotel_id: int
    rating: int
    comment: str


# In-memory reviews store
reviews_db: List[dict] = [
    {
        "id": 1,
        "user_id": 1,
        "hotel_id": 1,
        "rating": 5,
        "comment": "Excellent stay! Beautiful ocean view.",
    },
    {
        "id": 2,
        "user_id": 2,
        "hotel_id": 1,
        "rating": 4,
        "comment": "Great location, clean rooms.",
    },
    {
        "id": 3,
        "user_id": 3,
        "hotel_id": 2,
        "rating": 5,
        "comment": "Loved the beachfront villa!",
    },
]

next_review_id = 4


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "review-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "review-service"}


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/reviews", response_model=List[Review])
def get_reviews(hotel_id: Optional[int] = None, user_id: Optional[int] = None):
    results = reviews_db
    if hotel_id is not None:
        results = [r for r in results if r["hotel_id"] == hotel_id]
    if user_id is not None:
        results = [r for r in results if r["user_id"] == user_id]
    return results


@app.get("/reviews/{review_id}", response_model=Review)
def get_review(review_id: int):
    for r in reviews_db:
        if r["id"] == review_id:
            return r
    raise HTTPException(status_code=404, detail="Review not found")


@app.post("/reviews", response_model=Review, status_code=status.HTTP_201_CREATED)
def create_review(payload: ReviewCreate):
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(
            status_code=400, detail="Rating must be between 1 and 5"
        )

    global next_review_id
    new_review = {
        "id": next_review_id,
        "user_id": payload.user_id,
        "hotel_id": payload.hotel_id,
        "rating": payload.rating,
        "comment": payload.comment,
    }
    next_review_id += 1
    reviews_db.append(new_review)
    return new_review


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8008"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

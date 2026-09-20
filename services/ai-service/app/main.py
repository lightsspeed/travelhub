import os
from typing import List
from fastapi import FastAPI, Response, status
from pydantic import BaseModel

app = FastAPI(title="TravelHub AI Service")


class AssistantRequest(BaseModel):
    message: str


class AssistantResponse(BaseModel):
    message: str
    response: str


class ConversationItem(BaseModel):
    id: int
    message: str
    response: str


# In-memory conversations store
conversations_db: List[dict] = [
    {
        "id": 1,
        "message": "Find me a hotel in Mumbai",
        "response": "I can help you search hotels, check availability, and manage bookings.",
    }
]

next_conversation_id = 2


@app.get("/health")
def get_health():
    return {"status": "healthy", "service": "ai-service"}


@app.get("/ready")
def get_ready():
    return {"status": "ready", "service": "ai-service"}


@app.get("/metrics")
def get_metrics():
    metrics_data = (
        "# HELP travelhub_service_up Service availability status\n"
        "# TYPE travelhub_service_up gauge\n"
        "travelhub_service_up 1\n"
    )
    return Response(content=metrics_data, media_type="text/plain")


@app.post(
    "/assistant",
    response_model=AssistantResponse,
    status_code=status.HTTP_200_OK,
)
def assistant(payload: AssistantRequest):
    global next_conversation_id
    response_text = (
        "I can help you search hotels, check availability, and manage bookings."
    )
    interaction = {
        "id": next_conversation_id,
        "message": payload.message,
        "response": response_text,
    }
    next_conversation_id += 1
    conversations_db.append(interaction)
    return {"message": payload.message, "response": response_text}


@app.get("/conversations", response_model=List[ConversationItem])
def get_conversations():
    return conversations_db


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8010"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

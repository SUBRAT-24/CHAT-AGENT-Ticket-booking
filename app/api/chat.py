"""Chat API router - handles chatbot conversations."""

from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.ai.agent import museum_agent

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message to the chatbot and get a response."""
    try:
        result = await museum_agent.process_message(
            message=request.message,
            session_id=request.session_id,
        )
        return ChatResponse(
            reply=result["reply"],
            session_id=result["session_id"],
            action=result.get("action"),
            data=result.get("data"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get chat session history."""
    from app.database.connection import get_collection
    chat_col = get_collection("chat_logs")
    session = await chat_col.find_one(
        {"session_id": session_id}, {"_id": 0}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Convert datetimes for JSON serialization
    from datetime import datetime
    for key, value in session.items():
        if isinstance(value, datetime):
            session[key] = value.isoformat()

    return session

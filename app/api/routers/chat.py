from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.routers.auth import current_active_user
from app.db.models import User
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class ChatResponse(BaseModel):
    response: str

@router.post("/", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    user: User = Depends(current_active_user)
):
    service = ChatService()
    try:
        reply = await service.chat(
            user_id=str(user.id),
            conversation_id=req.conversation_id,
            message=req.message
        )
        return ChatResponse(response=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
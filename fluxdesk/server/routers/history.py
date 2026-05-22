from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models.schemas import ApiResponse
from models.database import get_db
from services.chat_service import ChatService
from utils.security import verify_api_token

router = APIRouter()


@router.get("/history/{window_id}")
async def get_history(
    window_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    service = ChatService(db)
    messages = service.get_history(window_id)
    return ApiResponse(data=[
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
        for m in reversed(messages)  # chrono order: oldest first
    ])


@router.get("/history")
async def get_all_history(
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    from models.database import Message
    messages = db.query(Message).order_by(Message.created_at.desc()).limit(100).all()
    return ApiResponse(data=[
        {"id": m.id, "window_id": m.window_id, "role": m.role, "content": m.content, "created_at": m.created_at}
        for m in reversed(messages)  # chrono order: oldest first
    ])

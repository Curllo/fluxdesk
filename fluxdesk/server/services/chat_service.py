from sqlalchemy.orm import Session
from models.database import Message
import uuid


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def add_message(self, window_id: str, role: str, content: str, **kwargs):
        msg = Message(
            id=f"msg_{uuid.uuid4().hex}",
            window_id=window_id,
            role=role,
            content=content,
            **kwargs,
        )
        self.db.add(msg)
        self.db.commit()
        return msg

    def get_history(self, window_id: str, limit: int = 50):
        return (
            self.db.query(Message)
            .filter(Message.window_id == window_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

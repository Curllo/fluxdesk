import json
from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import Window


class WindowCRUD:
    def __init__(self, db: Session):
        self.db = db

    def create(self, window_type: str, position: dict = None, size: dict = None,
               data: dict = None, **kwargs) -> Window:
        w = Window(
            type=window_type,
            position_x=position.get("x", 100) if position else 100,
            position_y=position.get("y", 100) if position else 100,
            width=size.get("width", 400) if size else 400,
            height=size.get("height", 300) if size else 300,
            data_json=json.dumps(data or {}),
            **kwargs
        )
        self.db.add(w)
        self.db.commit()
        self.db.refresh(w)
        return w

    def get(self, window_id: str) -> Optional[Window]:
        return self.db.query(Window).filter(Window.id == window_id).first()

    def list_all(self, window_type: str = None) -> List[Window]:
        q = self.db.query(Window)
        if window_type:
            q = q.filter(Window.type == window_type)
        return q.order_by(Window.created_at.desc()).all()

    def update(self, window_id: str, **kwargs) -> Optional[Window]:
        w = self.get(window_id)
        if not w:
            return None
        for k, v in kwargs.items():
            if hasattr(w, k):
                setattr(w, k, v)
        self.db.commit()
        self.db.refresh(w)
        return w

    def delete(self, window_id: str) -> bool:
        w = self.get(window_id)
        if w:
            self.db.delete(w)
            self.db.commit()
            return True
        return False

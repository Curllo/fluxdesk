from sqlalchemy.orm import Session
from models.database import Window
import json


class WindowService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, window_id: str, window_type: str, config: dict):
        w = Window(
            id=window_id,
            type=window_type,
            position_x=config.get("x", 100),
            position_y=config.get("y", 100),
            width=config.get("width", 400),
            height=config.get("height", 300),
            data_json=json.dumps(config.get("data", {})),
        )
        self.db.add(w)
        self.db.commit()
        return w

    def get(self, window_id: str):
        return self.db.query(Window).filter(Window.id == window_id).first()

    def list_all(self):
        return self.db.query(Window).all()

    def delete(self, window_id: str):
        w = self.get(window_id)
        if w:
            self.db.delete(w)
            self.db.commit()
        return w

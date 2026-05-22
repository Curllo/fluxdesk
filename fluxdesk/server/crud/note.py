from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import Note


class NoteCRUD:
    def __init__(self, db: Session):
        self.db = db

    def create(self, title: str = None, content: str = "", tags: str = None, window_id: str = None) -> Note:
        note = Note(title=title, content=content, tags=tags, window_id=window_id)
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def get(self, note_id: str) -> Optional[Note]:
        return self.db.query(Note).filter(Note.id == note_id).first()

    def list_all(self, tag: str = None) -> List[Note]:
        q = self.db.query(Note)
        if tag:
            q = q.filter(Note.tags.contains(tag))
        return q.order_by(Note.updated_at.desc()).all()

    def update(self, note_id: str, **kwargs) -> Optional[Note]:
        note = self.get(note_id)
        if not note:
            return None
        for k, v in kwargs.items():
            if hasattr(note, k):
                setattr(note, k, v)
        self.db.commit()
        self.db.refresh(note)
        return note

    def delete(self, note_id: str) -> bool:
        note = self.get(note_id)
        if note:
            self.db.delete(note)
            self.db.commit()
            return True
        return False

    def search(self, keyword: str) -> List[Note]:
        return self.db.query(Note).filter(
            Note.title.contains(keyword) | Note.content.contains(keyword)
        ).all()

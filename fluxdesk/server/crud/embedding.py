import json
from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import NoteEmbedding


class EmbeddingCRUD:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, note_id: str, embedding: List[float], model: str = "") -> NoteEmbedding:
        existing = self.db.query(NoteEmbedding).filter(NoteEmbedding.note_id == note_id).first()
        embedding_json = json.dumps(embedding)
        if existing:
            existing.embedding_json = embedding_json
            existing.model = model or existing.model
        else:
            existing = NoteEmbedding(note_id=note_id, embedding_json=embedding_json, model=model)
            self.db.add(existing)
        self.db.commit()
        self.db.refresh(existing)
        return existing

    def get_by_note(self, note_id: str) -> Optional[NoteEmbedding]:
        return self.db.query(NoteEmbedding).filter(NoteEmbedding.note_id == note_id).first()

    def get_all(self) -> List[NoteEmbedding]:
        return self.db.query(NoteEmbedding).all()

    def delete_by_note(self, note_id: str):
        self.db.query(NoteEmbedding).filter(NoteEmbedding.note_id == note_id).delete()
        self.db.commit()

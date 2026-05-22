"""Data export / import routes."""

import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Dict, List

from models.schemas import ApiResponse
from models.database import get_db, Note, Todo, Reminder, Message, PomodoroSession, Window, NoteEmbedding

router = APIRouter()

# Whitelist: only these column names are allowed in data import
_IMPORT_WHITELIST = {
    "notes": {"id", "window_id", "title", "content", "tags", "created_at", "updated_at"},
    "todos": {"id", "window_id", "content", "completed", "priority", "due_at", "completed_at", "created_at", "updated_at"},
    "reminders": {"id", "title", "time", "repeat", "dismissed", "created_at"},
    "messages": {"id", "window_id", "role", "content", "tool_calls", "model", "tokens_used", "latency_ms", "created_at"},
    "pomodoro_sessions": {"id", "duration", "started_at", "completed_at", "interrupted"},
    "embeddings": {"note_id", "id", "embedding_json", "model", "created_at"},
}


def _row_to_dict(row, exclude: set = None) -> dict:
    """Convert an ORM row to a dict, skipping SQLAlchemy internals."""
    d = {}
    for col in row.__table__.columns:
        key = col.name
        if exclude and key in exclude:
            continue
        d[key] = getattr(row, key)
    return d


@router.get("/data/export")
async def export_data(
    db: Session = Depends(get_db),
) -> ApiResponse:
    """Export all FluxDesk data as a JSON snapshot."""
    notes = [_row_to_dict(n) for n in db.query(Note).all()]
    todos = [_row_to_dict(t) for t in db.query(Todo).all()]
    reminders = [_row_to_dict(r) for r in db.query(Reminder).all()]
    messages = [_row_to_dict(m) for m in db.query(Message).order_by(Message.created_at).all()]
    sessions = [_row_to_dict(s) for s in db.query(PomodoroSession).all()]
    windows = [_row_to_dict(w) for w in db.query(Window).all()]
    embeddings = [
        {"note_id": e.note_id, "embedding_json": e.embedding_json, "model": e.model}
        for e in db.query(NoteEmbedding).all()
    ]

    return ApiResponse(data={
        "version": "1.1.0",
        "exported_at": datetime.now().isoformat(),
        "counts": {
            "notes": len(notes),
            "todos": len(todos),
            "reminders": len(reminders),
            "messages": len(messages),
            "pomodoro_sessions": len(sessions),
            "windows": len(windows),
            "embeddings": len(embeddings),
        },
        "data": {
            "notes": notes,
            "todos": todos,
            "reminders": reminders,
            "messages": messages,
            "pomodoro_sessions": sessions,
            "windows": windows,
            "embeddings": embeddings,
        },
    })


class ImportPayload(BaseModel):
    data: Dict[str, List[Dict[str, Any]]]


@router.post("/data/import")
async def import_data(
    payload: ImportPayload,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """Import data from a FluxDesk export JSON. Uses upsert-by-id strategy."""
    data = payload.data
    stats = {}

    def _filtered(item: dict, allowed: set) -> dict:
        """Return a dict with only allowed keys."""
        return {k: v for k, v in item.items() if k in allowed}

    # Notes
    allowed = _IMPORT_WHITELIST["notes"]
    if "notes" in data:
        count = 0
        for item in data["notes"]:
            filtered = _filtered(item, allowed)
            existing = db.query(Note).filter(Note.id == item.get("id")).first()
            if existing:
                for k, v in filtered.items():
                    if k != "id":
                        setattr(existing, k, v)
            else:
                db.add(Note(**filtered))
            count += 1
        stats["notes"] = count

    # Todos
    allowed = _IMPORT_WHITELIST["todos"]
    if "todos" in data:
        count = 0
        for item in data["todos"]:
            filtered = _filtered(item, allowed)
            existing = db.query(Todo).filter(Todo.id == item.get("id")).first()
            if existing:
                for k, v in filtered.items():
                    if k != "id":
                        setattr(existing, k, v)
            else:
                db.add(Todo(**filtered))
            count += 1
        stats["todos"] = count

    # Reminders
    allowed = _IMPORT_WHITELIST["reminders"]
    if "reminders" in data:
        count = 0
        for item in data["reminders"]:
            filtered = _filtered(item, allowed)
            existing = db.query(Reminder).filter(Reminder.id == item.get("id")).first()
            if existing:
                for k, v in filtered.items():
                    if k != "id":
                        setattr(existing, k, v)
            else:
                db.add(Reminder(**filtered))
            count += 1
        stats["reminders"] = count

    # Messages
    allowed = _IMPORT_WHITELIST["messages"]
    if "messages" in data:
        count = 0
        for item in data["messages"]:
            filtered = _filtered(item, allowed)
            existing = db.query(Message).filter(Message.id == item.get("id")).first()
            if not existing:
                db.add(Message(**filtered))
                count += 1
        stats["messages"] = count

    # Pomodoro sessions
    allowed = _IMPORT_WHITELIST["pomodoro_sessions"]
    if "pomodoro_sessions" in data:
        count = 0
        for item in data["pomodoro_sessions"]:
            filtered = _filtered(item, allowed)
            existing = db.query(PomodoroSession).filter(
                PomodoroSession.id == item.get("id")
            ).first()
            if not existing:
                db.add(PomodoroSession(**filtered))
                count += 1
        stats["pomodoro_sessions"] = count

    # Windows (skip — windows are transient, managed by Rust)
    if "windows" in data:
        stats["windows"] = len(data["windows"])

    # Embeddings
    allowed = _IMPORT_WHITELIST["embeddings"]
    if "embeddings" in data:
        count = 0
        for item in data["embeddings"]:
            filtered = _filtered(item, allowed)
            note_id = item.get("note_id")
            if not note_id:
                continue
            existing = db.query(NoteEmbedding).filter(
                NoteEmbedding.note_id == note_id
            ).first()
            if existing:
                existing.embedding_json = filtered.get("embedding_json", existing.embedding_json)
                existing.model = filtered.get("model", existing.model)
            else:
                db.add(NoteEmbedding(**filtered))
            count += 1
        stats["embeddings"] = count

    db.commit()

    return ApiResponse(data={
        "imported": True,
        "stats": stats,
    })

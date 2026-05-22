from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models.schemas import ApiResponse
from models.database import get_db, SessionLocal
from crud.note import NoteCRUD
from crud.embedding import EmbeddingCRUD
from utils.security import verify_api_token
from core.rag_engine import get_rag_engine

router = APIRouter()


def _index_note_bg(note_id: str, title: str, content: str):
    """Background task wrapper that creates its own DB session."""
    db = SessionLocal()
    try:
        get_rag_engine().index_note(db, note_id, title, content)
    finally:
        db.close()


class NoteCreate(BaseModel):
    title: Optional[str] = None
    content: str = ""
    tags: Optional[str] = None
    window_id: Optional[str] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None


@router.post("/notes")
async def create_note(
    req: NoteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = NoteCRUD(db)
    note = crud.create(
        title=req.title,
        content=req.content,
        tags=req.tags,
        window_id=req.window_id,
    )
    # Auto-index for RAG (background, uses its own DB session)
    background_tasks.add_task(_index_note_bg, note.id, note.title or "", note.content or "")
    return ApiResponse(data={
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "created_at": note.created_at,
    })


@router.get("/notes")
async def list_notes(
    tag: str = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = NoteCRUD(db)
    notes = crud.list_all(tag)
    return ApiResponse(data=[
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "tags": n.tags,
            "updated_at": n.updated_at,
        }
        for n in notes
    ])


@router.get("/notes/search")
async def search_notes(
    q: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    rag = get_rag_engine()
    results = await rag.search(db, q, top_k=10)
    return ApiResponse(data=results)


@router.get("/notes/{note_id}")
async def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = NoteCRUD(db)
    note = crud.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return ApiResponse(data={
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "updated_at": note.updated_at,
    })


@router.patch("/notes/{note_id}")
async def update_note(
    note_id: str,
    req: NoteUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = NoteCRUD(db)
    kwargs = req.model_dump(exclude_unset=True)
    note = crud.update(note_id, **kwargs)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    # Re-index for RAG (background, uses its own DB session)
    background_tasks.add_task(_index_note_bg, note.id, note.title or "", note.content or "")
    return ApiResponse(data={"id": note.id, "updated": True})


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = NoteCRUD(db)
    ok = crud.delete(note_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    EmbeddingCRUD(db).delete_by_note(note_id)
    return ApiResponse(data={"deleted": True})

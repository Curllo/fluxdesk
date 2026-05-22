from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models.schemas import ApiResponse
from models.database import get_db
from crud.todo import TodoCRUD
from utils.security import verify_api_token

router = APIRouter()


class TodoCreate(BaseModel):
    content: str
    priority: int = 1
    due_at: Optional[str] = None
    window_id: Optional[str] = None


class TodoUpdate(BaseModel):
    content: Optional[str] = None
    priority: Optional[int] = None
    completed: Optional[bool] = None


@router.post("/todos")
async def create_todo(
    req: TodoCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = TodoCRUD(db)
    todo = crud.create(
        content=req.content,
        priority=req.priority,
        due_at=req.due_at,
        window_id=req.window_id,
    )
    return ApiResponse(data={
        "id": todo.id,
        "content": todo.content,
        "completed": bool(todo.completed),
        "priority": todo.priority,
        "created_at": todo.created_at,
    })


@router.get("/todos")
async def list_todos(
    completed: bool = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = TodoCRUD(db)
    todos = crud.list_all(completed)
    return ApiResponse(data=[
        {
            "id": t.id,
            "content": t.content,
            "completed": bool(t.completed),
            "priority": t.priority,
            "due_at": t.due_at,
            "created_at": t.created_at,
        }
        for t in todos
    ])


@router.post("/todos/{todo_id}/complete")
async def complete_todo(
    todo_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = TodoCRUD(db)
    todo = crud.complete(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return ApiResponse(data={"id": todo.id, "completed": True})


@router.patch("/todos/{todo_id}")
async def update_todo(
    todo_id: str,
    req: TodoUpdate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = TodoCRUD(db)
    kwargs = req.model_dump(exclude_unset=True)
    todo = crud.update(todo_id, **kwargs)
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return ApiResponse(data={"id": todo.id, "updated": True})


@router.delete("/todos/{todo_id}")
async def delete_todo(
    todo_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = TodoCRUD(db)
    ok = crud.delete(todo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Todo not found")
    return ApiResponse(data={"deleted": True})

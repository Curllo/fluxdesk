from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from models.schemas import ApiResponse
from models.database import get_db
from crud.reminder import ReminderCRUD
from utils.security import verify_api_token

router = APIRouter()


class ReminderCreate(BaseModel):
    title: str
    time: str  # ISO 8601
    repeat: str = "once"


@router.post("/reminders")
async def create_reminder(
    req: ReminderCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = ReminderCRUD(db)
    r = crud.create(title=req.title, time=req.time, repeat=req.repeat)
    return ApiResponse(data={
        "id": r.id,
        "title": r.title,
        "time": r.time,
        "repeat": r.repeat,
    })


@router.get("/reminders")
async def list_reminders(
    dismissed: bool = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = ReminderCRUD(db)
    reminders = crud.list_all(dismissed)
    return ApiResponse(data=[
        {
            "id": r.id,
            "title": r.title,
            "time": r.time,
            "repeat": r.repeat,
            "dismissed": bool(r.dismissed),
        }
        for r in reminders
    ])


@router.post("/reminders/{reminder_id}/dismiss")
async def dismiss_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = ReminderCRUD(db)
    r = crud.dismiss(reminder_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return ApiResponse(data={"id": r.id, "dismissed": True})


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = ReminderCRUD(db)
    ok = crud.delete(reminder_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return ApiResponse(data={"deleted": True})

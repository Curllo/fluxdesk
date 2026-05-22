from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.schemas import ApiResponse, CreateWindowRequest
from models.database import get_db
from crud.window import WindowCRUD
from utils.security import verify_api_token

router = APIRouter()


@router.post("/windows")
async def create_window(
    req: CreateWindowRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = WindowCRUD(db)
    w = crud.create(
        window_type=req.window_type,
        position=req.position,
        size=req.size,
        data=req.data,
    )
    return ApiResponse(data={
        "id": w.id,
        "type": w.type,
        "position": {"x": w.position_x, "y": w.position_y},
        "size": {"width": w.width, "height": w.height},
        "data": req.data,
    })


@router.get("/windows")
async def list_windows(
    window_type: str = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = WindowCRUD(db)
    windows = crud.list_all(window_type)
    return ApiResponse(data=[
        {
            "id": w.id,
            "type": w.type,
            "position": {"x": w.position_x, "y": w.position_y},
            "size": {"width": w.width, "height": w.height},
            "data": w.data_json,
            "created_at": w.created_at,
        }
        for w in windows
    ])


@router.get("/windows/{window_id}")
async def get_window(
    window_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = WindowCRUD(db)
    w = crud.get(window_id)
    if not w:
        raise HTTPException(status_code=404, detail="Window not found")
    return ApiResponse(data={
        "id": w.id,
        "type": w.type,
        "position": {"x": w.position_x, "y": w.position_y},
        "size": {"width": w.width, "height": w.height},
        "data": w.data_json,
    })


@router.delete("/windows/{window_id}")
async def delete_window(
    window_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    crud = WindowCRUD(db)
    ok = crud.delete(window_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Window not found")
    return ApiResponse(data={"deleted": True})

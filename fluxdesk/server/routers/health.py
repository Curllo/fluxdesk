from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/internal/health")
async def internal_health():
    return {"status": "ok", "version": "1.1.0"}


@router.get("/api/v1/health")
async def api_health():
    return {"status": "ok", "version": "1.1.0"}

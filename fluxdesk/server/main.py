import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import chat, health, windows, history, data, settings as settings_router, todos, notes, reminders
from models.database import run_migrations
from utils.config import get_settings
from utils.logger import setup_logging
from core.idle_manager import get_idle_manager

settings = get_settings()
setup_logging()
run_migrations()

app = FastAPI(
    title="FluxDesk AI Service",
    version="1.1.0",
    docs_url="/docs" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(windows.router, prefix="/api/v1", tags=["windows"])
app.include_router(history.router, prefix="/api/v1", tags=["history"])
app.include_router(settings_router.router, prefix="/api/v1", tags=["settings"])
app.include_router(todos.router, prefix="/api/v1", tags=["todos"])
app.include_router(notes.router, prefix="/api/v1", tags=["notes"])
app.include_router(reminders.router, prefix="/api/v1", tags=["reminders"])
app.include_router(data.router, prefix="/api/v1", tags=["data"])


@app.middleware("http")
async def idle_middleware(request: Request, call_next):
    get_idle_manager().record_activity()
    response = await call_next(request)
    return response


@app.on_event("startup")
async def on_startup():
    get_idle_manager().start_monitoring()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logger = logging.getLogger("fluxdesk")
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "Internal server error", "data": None},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("FLUXDESK_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)

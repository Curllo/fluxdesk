import logging
import os
import sys as _sys
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def _resolve_db_url() -> str:
    """Resolve database URL with PyInstaller-safe fallback."""
    if db_url := os.environ.get("FLUXDESK_DATABASE_URL"):
        return db_url
    app_dir = os.environ.get("FLUXDESK_APP_DIR")
    if app_dir and app_dir != ".":
        return f"sqlite:///{os.path.abspath(app_dir)}/fluxdesk.db"
    if getattr(_sys, 'frozen', False):
        return f"sqlite:///{os.path.dirname(_sys.executable)}/fluxdesk.db"
    return f"sqlite:///{os.getcwd()}/fluxdesk.db"


DATABASE_URL = _resolve_db_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def now_iso() -> str:
    return datetime.now().isoformat()


def gen_id() -> str:
    return uuid.uuid4().hex[:16]


# ── Window ───────────────────────────────────────────────────────────
class Window(Base):
    __tablename__ = "windows"
    id = Column(String, primary_key=True, default=gen_id)
    type = Column(String, nullable=False)
    position_x = Column(Float, default=100)
    position_y = Column(Float, default=100)
    width = Column(Float, default=400)
    height = Column(Float, default=300)
    always_on_top = Column(Integer, default=1)
    is_minimized = Column(Integer, default=0)
    display_index = Column(Integer, default=0)
    opacity = Column(Float, default=1.0)
    data_json = Column(Text, default="{}")
    created_at = Column(String, default=now_iso)
    updated_at = Column(String, default=now_iso)


# ── Message (chat history) ───────────────────────────────────────────
class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=gen_id)
    window_id = Column(String, ForeignKey("windows.id", ondelete="CASCADE"), nullable=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True)
    model = Column(String, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(String, default=now_iso)


# ── Todo ─────────────────────────────────────────────────────────────
class Todo(Base):
    __tablename__ = "todos"
    id = Column(String, primary_key=True, default=gen_id)
    window_id = Column(String, ForeignKey("windows.id", ondelete="CASCADE"), nullable=True)
    content = Column(String, nullable=False)
    completed = Column(Integer, default=0)
    priority = Column(Integer, default=1)  # 1=低 2=中 3=高
    due_at = Column(String, nullable=True)
    completed_at = Column(String, nullable=True)
    created_at = Column(String, default=now_iso)
    updated_at = Column(String, default=now_iso)


# ── Note ─────────────────────────────────────────────────────────────
class Note(Base):
    __tablename__ = "notes"
    id = Column(String, primary_key=True, default=gen_id)
    window_id = Column(String, ForeignKey("windows.id", ondelete="CASCADE"), nullable=True)
    title = Column(String, nullable=True)
    content = Column(Text, default="")
    tags = Column(Text, nullable=True)  # comma-separated
    created_at = Column(String, default=now_iso)
    updated_at = Column(String, default=now_iso)


# ── Reminder ─────────────────────────────────────────────────────────
class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    time = Column(String, nullable=False)  # ISO 8601
    repeat = Column(String, default="once")  # once / daily / weekly
    dismissed = Column(Integer, default=0)
    created_at = Column(String, default=now_iso)


# ── Note Embedding (RAG) ─────────────────────────────────────────────
class NoteEmbedding(Base):
    __tablename__ = "note_embeddings"
    id = Column(String, primary_key=True, default=gen_id)
    note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_json = Column(Text, nullable=False)  # JSON array of floats
    model = Column(String, nullable=True)  # e.g. "text-embedding-3-small"
    created_at = Column(String, default=now_iso)


# ── Pomodoro Session ─────────────────────────────────────────────────
class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"
    id = Column(String, primary_key=True, default=gen_id)
    duration = Column(Integer, default=25)  # minutes
    started_at = Column(String, default=now_iso)
    completed_at = Column(String, nullable=True)
    interrupted = Column(Integer, default=0)


def init_db():
    Base.metadata.create_all(bind=engine)


def run_migrations():
    """Run Alembic migrations, falling back to init_db() + stamp for new databases."""
    from alembic.config import Config
    from alembic import command

    alembic_ini = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    alembic_cfg = Config(alembic_ini)

    logger = logging.getLogger("fluxdesk")
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception:
        logger.exception("Alembic upgrade failed; falling back to init_db() then stamping head.")
        init_db()
        command.stamp(alembic_cfg, "head")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

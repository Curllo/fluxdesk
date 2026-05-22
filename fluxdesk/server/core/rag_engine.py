import json
import math
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from models.database import Note, NoteEmbedding
from crud.embedding import EmbeddingCRUD
from core.intent_engine import get_intent_engine

logger = logging.getLogger("fluxdesk.rag")


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tokenize(text: str) -> set:
    """Simple Chinese/English tokenizer for keyword fallback."""
    import re
    # Split on non-word characters, keep CJK chars as unigrams
    tokens = set()
    # Add word tokens (2+ chars for CJK, whole words for ASCII)
    for token in re.findall(r'[一-鿿]{1,2}|[a-zA-Z]{2,}', text.lower()):
        tokens.add(token)
    return tokens


class RAGEngine:
    def __init__(self):
        self._engine = get_intent_engine()

    def _embedding_model(self) -> str:
        """Return the appropriate embedding model for the current provider."""
        provider = self._engine.provider
        if provider == "openai":
            return "text-embedding-3-small"
        elif provider == "gemini":
            return "gemini/text-embedding-004"
        # Other providers may not support embeddings; will fall back to keyword
        return "text-embedding-3-small"

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding via LiteLLM. Returns None if unavailable."""
        if self._engine.mock_mode:
            return None
        try:
            import litellm
            response = await litellm.aembedding(
                model=self._embedding_model(),
                input=text,
                api_key=self._engine.api_key,
            )
            return response.data[0]["embedding"]
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    def index_note(self, db: Session, note_id: str, title: str, content: str):
        """Generate embedding and store it for a note (sync wrapper)."""
        import asyncio
        text = f"{title or ''}\n{content or ''}"
        if not text.strip():
            return

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context, create task (best-effort, fire-and-forget)
                import asyncio
                async def _do():
                    emb = await self.generate_embedding(text)
                    if emb:
                        EmbeddingCRUD(db).upsert(note_id, emb, self._embedding_model())
                asyncio.ensure_future(_do())
            else:
                emb = loop.run_until_complete(self.generate_embedding(text))
                if emb:
                    EmbeddingCRUD(db).upsert(note_id, emb, self._embedding_model())
        except RuntimeError:
            # No event loop — run synchronously (best-effort keyword only)
            pass

    async def search(self, db: Session, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search over notes. Falls back to keyword if no embeddings available."""
        # Try vector search first
        query_emb = await self.generate_embedding(query)

        if query_emb:
            return self._vector_search(db, query_emb, top_k)
        else:
            return self._keyword_search(db, query, top_k)

    def _vector_search(self, db: Session, query_emb: List[float], top_k: int) -> List[Dict]:
        """Cosine similarity search over stored embeddings."""
        emb_crud = EmbeddingCRUD(db)
        all_embs = emb_crud.get_all()

        scored = []
        for emb_record in all_embs:
            try:
                stored_emb = json.loads(emb_record.embedding_json)
                score = _cosine_similarity(query_emb, stored_emb)
                scored.append((emb_record.note_id, score))
            except (json.JSONDecodeError, TypeError):
                continue

        scored.sort(key=lambda x: x[1], reverse=True)
        top_ids = [sid for sid, _ in scored[:top_k]]
        return self._fetch_notes(db, top_ids)

    def _keyword_search(self, db: Session, query: str, top_k: int) -> List[Dict]:
        """Keyword overlap search for mock mode / no-embedding fallback."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        notes = db.query(Note).order_by(Note.updated_at.desc()).limit(100).all()
        scored = []
        for note in notes:
            text = f"{note.title or ''} {note.content or ''}"
            note_tokens = _tokenize(text)
            overlap = len(query_tokens & note_tokens)
            if overlap > 0:
                # Jaccard-like score with length normalization
                score = overlap / (len(query_tokens) + len(note_tokens) - overlap + 1)
                scored.append((note.id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_ids = [sid for sid, _ in scored[:top_k]]
        return self._fetch_notes(db, top_ids)

    def _fetch_notes(self, db: Session, note_ids: List[str]) -> List[Dict]:
        """Fetch note metadata by IDs, preserving order."""
        notes_map = {}
        for note in db.query(Note).filter(Note.id.in_(note_ids)).all():
            notes_map[note.id] = note
        result = []
        for nid in note_ids:
            note = notes_map.get(nid)
            if note:
                result.append({
                    "id": note.id,
                    "title": note.title or "未命名",
                    "content": (note.content or "")[:300],  # truncate for LLM context
                    "updated_at": note.updated_at,
                })
        return result


# Singleton
_rag: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _rag
    if _rag is None:
        _rag = RAGEngine()
    return _rag

import os
import sys
from functools import lru_cache


def _resolve_app_dir(raw: str) -> str:
    """Resolve '.' to an absolute path, safe for PyInstaller frozen bundles."""
    if raw == ".":
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.getcwd()
    return os.path.abspath(raw)


class Settings:
    port: int = int(os.environ.get("FLUXDESK_PORT", "8000"))
    api_token: str = os.environ.get("FLUXDESK_API_TOKEN", "dev-token")
    internal_token: str = os.environ.get("FLUXDESK_INTERNAL_TOKEN", "internal-token")
    rust_port: int = int(os.environ.get("FLUXDESK_RUST_PORT", "9595"))
    app_dir: str = _resolve_app_dir(os.environ.get("FLUXDESK_APP_DIR", "."))
    debug: bool = os.environ.get("FLUXDESK_DEBUG", "false").lower() == "true"
    database_url: str = os.environ.get(
        "FLUXDESK_DATABASE_URL", "sqlite:///fluxdesk.db"
    )
    llm_provider: str = os.environ.get("FLUXDESK_LLM_PROVIDER", "openai")
    llm_model: str = os.environ.get("FLUXDESK_LLM_MODEL", "gpt-4o-mini")
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")


@lru_cache()
def get_settings() -> Settings:
    return Settings()

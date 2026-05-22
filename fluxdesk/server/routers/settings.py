import base64
import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from models.schemas import ApiResponse
from utils.security import verify_api_token
from core.intent_engine import get_intent_engine, PROVIDER_CONFIG, _get_api_key

router = APIRouter()

# ── LLM config persistence ──────────────────────────────────────────────
_CONFIG_FILE = Path(os.environ.get("FLUXDESK_APP_DIR", ".")) / "llm_config.json"


def _decode_if_b64(s: str) -> str:
    """Try base64 decode; only accept if result is valid UTF-8 printable text."""
    try:
        decoded_bytes = base64.b64decode(s, validate=True)
        decoded = decoded_bytes.decode("utf-8")
        if all(c.isprintable() or c.isspace() for c in decoded):
            return decoded
    except Exception:
        pass
    return s


def _load_saved_config() -> dict:
    """Load saved LLM config from disk."""
    try:
        if _CONFIG_FILE.exists():
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            # Decode base64-encoded API key if applicable
            if data.get("api_key"):
                data["api_key"] = _decode_if_b64(data["api_key"])
            return data
    except Exception as e:
        import sys
        print(f"[settings] Failed to load config: {e}", file=sys.stderr)
    return {}


def _save_config(config: dict):
    """Save LLM config to disk (API key is base64-encoded)."""
    try:
        data = dict(config)
        if data.get("api_key"):
            data["api_key"] = base64.b64encode(data["api_key"].encode("utf-8")).decode("ascii")
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            import stat
            os.chmod(str(_CONFIG_FILE.parent), stat.S_IRWXU)  # 0700: owner-only access
            if _CONFIG_FILE.exists():
                os.chmod(str(_CONFIG_FILE), stat.S_IRUSR | stat.S_IWUSR)  # 0600: owner-only rw
        except OSError:
            pass
        import sys
        print(f"[settings] Config saved to {_CONFIG_FILE}", file=sys.stderr)
    except Exception as e:
        import sys
        print(f"[settings] Failed to save config: {e}", file=sys.stderr)


def _apply_saved_config():
    """Apply saved config to the engine on startup."""
    saved = _load_saved_config()
    if not saved:
        return
    engine = get_intent_engine()
    engine.apply_runtime_config(
        provider=saved.get("provider", "openai"),
        model=saved.get("model", "gpt-4o-mini"),
        api_key=saved.get("api_key") or None,
        api_base=saved.get("api_base") or None,
    )
    import sys
    print(f"[settings] Applied saved config: provider={saved.get('provider')}, model={saved.get('model')}, mock_mode={engine.mock_mode}", file=sys.stderr)


# Apply saved config on import
try:
    import sys
    print(f"[settings] Config file path: {_CONFIG_FILE}", file=sys.stderr)
    _apply_saved_config()
except Exception as e:
    import sys
    print(f"[settings] Failed to apply saved config: {e}", file=sys.stderr)


class LLMConfig(BaseModel):
    provider: str = Field(default="openai")
    api_base: Optional[str] = Field(default=None, description="API base URL (e.g. https://api.openai.com/v1)")
    model: str = Field(default="gpt-4o-mini")
    api_key: Optional[str] = Field(default=None, description="API Key (设置时传入，读取时不返回)")


class LLMConfigResponse(BaseModel):
    provider: str
    api_base: Optional[str]
    model: str
    mock_mode: bool


class VerifyRequest(BaseModel):
    api_base: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


# In-memory overrides (survive across requests, reset on restart)
_runtime_overrides: dict = {}
# Global preferences store (key → value)
_preferences: dict = {}


class PreferenceUpdate(BaseModel):
    key: str
    value: str


@router.get("/settings/llm")
async def get_llm_config(
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    engine = get_intent_engine()
    return ApiResponse(data={
        "provider": engine.provider,
        "api_base": engine.api_base,
        "model": engine.model,
        "mock_mode": engine.mock_mode,
    })


@router.post("/settings/llm")
async def update_llm_config(
    config: LLMConfig,
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    global _runtime_overrides

    # Persist in memory for later verification calls
    _runtime_overrides["provider"] = config.provider
    _runtime_overrides["model"] = config.model
    if config.api_base:
        _runtime_overrides["api_base"] = config.api_base
    if config.api_key:
        _runtime_overrides["api_key"] = config.api_key

    # Merge new config with existing saved config (keep old api_key if not provided)
    engine = get_intent_engine()
    effective_api_key = config.api_key or engine.api_key
    engine.apply_runtime_config(
        provider=config.provider,
        model=config.model,
        api_key=effective_api_key,
        api_base=config.api_base,
    )

    # Save to disk (persist across restarts)
    saved = _load_saved_config()
    _save_config({
        "provider": config.provider,
        "model": config.model,
        "api_base": config.api_base or saved.get("api_base", ""),
        "api_key": config.api_key or saved.get("api_key", ""),
    })

    return ApiResponse(data={
        "provider": config.provider,
        "api_base": engine.api_base,
        "model": config.model,
        "mock_mode": engine.mock_mode,
    })


@router.post("/settings/llm/verify")
async def verify_llm_config(
    req: VerifyRequest = None,
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    engine = get_intent_engine()

    # Use request params if provided, otherwise engine defaults
    api_key = req.api_key if req and req.api_key else engine.api_key
    model = req.model if req and req.model else engine.model
    api_base = req.api_base if req and req.api_base else engine.api_base

    if not api_key:
        return ApiResponse(code=400, message="未配置 API Key", data={"ok": False})

    try:
        import litellm
        kwargs = {"api_key": api_key}
        if api_base:
            kwargs["api_base"] = api_base

        if "/" not in model:
            model = f"{engine.provider}/{model}"

        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5,
            **kwargs,
        )
        return ApiResponse(data={
            "ok": True,
            "model": response.model,
            "tokens_used": response.usage.total_tokens if response.usage else None,
        })
    except Exception as e:
        return ApiResponse(code=400, message=str(e), data={"ok": False, "error": str(e)})


@router.post("/settings/llm/scan")
async def scan_llm_models(
    req: LLMConfig = None,
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    """Scan available models from the configured API endpoint.
    Supports OpenAI-compatible endpoints (GET /models) and Ollama (GET /api/tags).
    Falls back to manual input if scanning fails."""
    engine = get_intent_engine()

    api_base = req.api_base if req and req.api_base else engine.api_base
    api_key = req.api_key if req and req.api_key else engine.api_key
    provider = req.provider if req and req.provider else engine.provider

    if not api_base:
        return ApiResponse(data=[])

    base = api_base.rstrip("/")
    # 注意：/v1 截断仅适用于 Ollama，OpenAI 兼容端点需要保留 /v1

    models: List[str] = []

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            if provider == "ollama" or "ollama" in base:
                if base.endswith("/v1"):
                    base = base[:-3]
                # Ollama: GET /api/tags
                resp = await client.get(f"{base}/api/tags")
                if resp.is_success:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
            else:
                # OpenAI-compatible: GET /models
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                resp = await client.get(f"{base}/models", headers=headers)
                if resp.is_success:
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", [])]

        if models:
            models.sort()
    except Exception:
        pass

    # Fallback: return common models for the provider
    if not models:
        from core.intent_engine import PROVIDER_DEFAULT_MODELS
        fallback = PROVIDER_DEFAULT_MODELS.get(provider, "")
        models = [fallback] if fallback else []

    return ApiResponse(data=models)


# ── Global preferences (shortcut, etc.) ──────────────────────────────────

@router.get("/settings/preferences")
async def get_preferences(
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    return ApiResponse(data=dict(_preferences))


@router.post("/settings/preferences")
async def update_preference(
    pref: PreferenceUpdate,
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    _preferences[pref.key] = pref.value
    return ApiResponse(data={pref.key: pref.value})


@router.delete("/settings/preferences/{key}")
async def delete_preference(
    key: str,
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    _preferences.pop(key, None)
    return ApiResponse(data={"deleted": True})

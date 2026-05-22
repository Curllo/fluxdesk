import os
import json
import asyncio
import litellm
from typing import List, Dict, Any, AsyncGenerator, Optional

from core.prompt_manager import PromptManager
from core.function_schemas import TOOLS
from core.idle_manager import get_idle_manager
from core.ollama_adapter import get_ollama_adapter
from models.database import SessionLocal

# Transient HTTP status codes that should be retried
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

litellm.drop_params = True
litellm.set_verbose = os.environ.get("FLUXDESK_DEBUG", "false").lower() == "true"

# Provider → (API key env var, base URL override)
PROVIDER_CONFIG = {
    "openai":    ("OPENAI_API_KEY", None),
    "anthropic": ("ANTHROPIC_API_KEY", None),
    "deepseek":  ("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1"),
    "gemini":    ("GEMINI_API_KEY", None),
}

# Provider-specific default models
PROVIDER_DEFAULT_MODELS = {
    "openai":    "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
    "deepseek":  "deepseek-chat",
    "gemini":    "gemini-2.0-flash",
}


def _get_api_key(provider: str) -> str:
    """Resolve API key: runtime override → provider env var → OPENAI_API_KEY fallback → empty."""
    env_var, _ = PROVIDER_CONFIG.get(provider, ("OPENAI_API_KEY", None))
    key = os.environ.get(env_var, "")
    if not key and env_var != "OPENAI_API_KEY":
        key = os.environ.get("OPENAI_API_KEY", "")
    return key


def _get_provider_config(provider: str):
    """Return (api_key_env_var, base_url_or_None) for a provider, defaulting to openai."""
    return PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["openai"])


class IntentEngine:
    """Singleton intent engine. Use get_intent_engine() to obtain the shared instance."""

    def __init__(self):
        self._load_config()

    def _load_config(self):
        self.provider = os.environ.get("FLUXDESK_LLM_PROVIDER", "openai")
        self.model = os.environ.get("FLUXDESK_LLM_MODEL", PROVIDER_DEFAULT_MODELS.get(self.provider, "gpt-4o-mini"))
        self.api_base = os.environ.get("FLUXDESK_LLM_API_BASE", "")
        self.api_key = _get_api_key(self.provider)
        self.mock_mode = os.environ.get("FLUXDESK_MOCK_LLM", "false").lower() == "true" or not self.api_key
        self.prompt_manager = PromptManager()

    def apply_runtime_config(self, provider: str, model: str, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """Hot-reload: apply settings from the settings API without restarting."""
        self.provider = provider
        self.model = model
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = _get_api_key(provider)
        if api_base:
            self.api_base = api_base
        self.mock_mode = not bool(self.api_key)
        # Update os.environ so child calls (e.g. litellm) see them too
        os.environ["FLUXDESK_LLM_PROVIDER"] = provider
        os.environ["FLUXDESK_LLM_MODEL"] = model
        if api_base:
            os.environ["FLUXDESK_LLM_API_BASE"] = api_base

    def _resolve_model(self) -> str:
        """Return the LiteLLM model string (provider/model)."""
        model = self.model
        if "/" not in model:
            model = f"{self.provider}/{model}"
        return model

    def _api_kwargs(self) -> dict:
        """Build the LiteLLM kwargs dict including api_key and optional base_url."""
        base_url = self.api_base or _get_provider_config(self.provider)[1]
        kwargs = {"api_key": self.api_key}
        if base_url:
            kwargs["api_base"] = base_url
        return kwargs

    def _build_messages(self, user_message: str, history: List[Dict] = None) -> List[Dict]:
        system_prompt = self.prompt_manager.load_system_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history[-30:]:
                messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        return messages

    # ── No‑key fallback ──────────────────────────────────────────────────

    def _no_key_parse(self) -> Dict[str, Any]:
        return {
            "intent": "chat",
            "confidence": 1.0,
            "action": None,
            "reply": "AI 服务未配置，请先在设置中填入 API Key 并保存。",
            "model": "none",
            "tokens_used": 0,
        }

    async def _no_key_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        for char in "AI 服务未配置，请先在设置中填入 API Key 并保存。":
            yield {"event": "message", "data": {"delta": char}}
        yield {"event": "done", "data": {}}

    # ── Real LLM via LiteLLM ─────────────────────────────────────────────

    async def parse(self, message: str, history: List[Dict] = None) -> Dict[str, Any]:
        get_idle_manager().wake()
        if self.mock_mode:
            return self._no_key_parse()

        messages = self._build_messages(message, history)

        # Second layer: Ollama local model
        ollama = get_ollama_adapter()
        if await ollama.is_available():
            try:
                ollama_resp = await ollama.chat(messages, tools=TOOLS)
                if ollama_resp.get("tool_calls"):
                    tc = ollama_resp["tool_calls"][0]
                    fn_name = tc["function"]["name"]
                    fn_args = json.loads(tc["function"]["arguments"])
                    if fn_name == "search_notes":
                        return await self._execute_search_notes(
                            messages, fn_args.get("query", ""), "ollama/" + ollama.model, 0
                        )
                    return {
                        "intent": fn_name,
                        "confidence": 0.88,
                        "action": fn_name,
                        "params": fn_args,
                        "tool_calls": ollama_resp["tool_calls"],
                        "reply": f"好的，正在为您执行：{fn_name}",
                        "model": "ollama/" + ollama.model,
                        "tokens_used": 0,
                    }
                return {
                    "intent": "chat",
                    "confidence": 0.75,
                    "action": None,
                    "reply": ollama_resp.get("content") or "好的，已收到。",
                    "model": "ollama/" + ollama.model,
                    "tokens_used": 0,
                }
            except Exception:
                pass  # Fall through to cloud LLM

        # Third layer: Cloud LLM via LiteLLM
        try:
            response = await with_retry(
                lambda: litellm.acompletion(
                    model=self._resolve_model(),
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=8192,
                    timeout=30,
                    **self._api_kwargs(),
                )
            )

            choice = response.choices[0]
            msg = choice.message

            if msg.tool_calls:
                # Process ALL tool calls, not just the first
                tool_results = []
                primary_fn_name = None
                primary_fn_args = None

                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)

                    if primary_fn_name is None:
                        primary_fn_name = fn_name
                        primary_fn_args = fn_args

                    # Agent loop: search_notes is handled transparently
                    if fn_name == "search_notes":
                        return await self._execute_search_notes(
                            messages, fn_args.get("query", ""), response.model,
                            response.usage.total_tokens if response.usage else None,
                        )

                    tool_results.append({"name": fn_name, "params": fn_args})

                return {
                    "intent": primary_fn_name,
                    "confidence": 0.95,
                    "action": primary_fn_name,
                    "params": primary_fn_args,
                    "tool_calls": tool_results,
                    "reply": f"好的，正在为您执行：{', '.join(t['name'] for t in tool_results)}",
                    "model": response.model,
                    "tokens_used": response.usage.total_tokens if response.usage else None,
                }

            return {
                "intent": "chat",
                "confidence": 0.8,
                "action": None,
                "reply": msg.content or "好的，已收到。",
                "model": response.model,
                "tokens_used": response.usage.total_tokens if response.usage else None,
            }

        except Exception as e:
            return {
                "intent": "error",
                "confidence": 0.0,
                "action": None,
                "reply": f"智能服务暂不可用：{str(e)}",
            }

    async def stream_parse(
        self, message: str, history: List[Dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        get_idle_manager().wake()
        if self.mock_mode:
            async for event in self._no_key_stream():
                yield event
            return

        messages = self._build_messages(message, history)

        # Second layer: Ollama local model (non-streaming then yield chunks)
        ollama = get_ollama_adapter()
        if await ollama.is_available():
            try:
                ollama_resp = await ollama.chat(messages, tools=TOOLS)
                if ollama_resp.get("tool_calls"):
                    tc = ollama_resp["tool_calls"][0]
                    fn_name = tc["function"]["name"]
                    fn_args_str = tc["function"]["arguments"]
                    yield {"event": "tool_call", "data": {"name": fn_name, "arguments": fn_args_str}}
                    try:
                        params = json.loads(fn_args_str)
                        yield {"event": "tool_result", "data": {"result": "done", "success": True, "params": params}}
                    except json.JSONDecodeError:
                        yield {"event": "tool_result", "data": {"result": "parse_error", "success": False}}
                    yield {"event": "done", "data": {}}
                    return
                # Yield content as simulated stream
                content = ollama_resp.get("content", "")
                chunk_size = 4
                for i in range(0, len(content), chunk_size):
                    yield {"event": "message", "data": {"delta": content[i:i+chunk_size]}}
                yield {"event": "done", "data": {}}
                return
            except Exception:
                pass  # Fall through to cloud LLM

        # Third layer: Cloud LLM via LiteLLM
        try:
            stream = await with_retry(
                lambda: litellm.acompletion(
                    model=self._resolve_model(),
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.2,
                    max_tokens=8192,
                    stream=True,
                    timeout=30,
                    **self._api_kwargs(),
                )
            )

            tool_calls_buffer = []
            content_buffer = []

            async for chunk in stream:
                delta = chunk.choices[0].delta

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls_buffer.append(tc)

                if delta.content:
                    content_buffer.append(delta.content)
                    yield {"event": "message", "data": {"delta": delta.content}}

            if tool_calls_buffer:
                merged = self._merge_tool_calls(tool_calls_buffer)
                for tc in merged:
                    fn_name = tc["function"]["name"]
                    fn_args_str = tc["function"]["arguments"]
                    yield {
                        "event": "tool_call",
                        "data": {"name": fn_name, "arguments": fn_args_str},
                    }

                    # Agent loop for search_notes
                    if fn_name == "search_notes":
                        try:
                            params = json.loads(fn_args_str)
                            async for event in self._agent_search_notes(messages, params.get("query", "")):
                                yield event
                            return  # done already emitted by agent loop
                        except json.JSONDecodeError:
                            yield {"event": "tool_result", "data": {"result": "parse_error", "success": False}}
                    else:
                        try:
                            params = json.loads(fn_args_str)
                            yield {
                                "event": "tool_result",
                                "data": {"result": "done", "success": True, "params": params},
                            }
                        except json.JSONDecodeError:
                            yield {
                                "event": "tool_result",
                                "data": {"result": "parse_error", "success": False},
                            }

            yield {"event": "done", "data": {}}

        except Exception as e:
            yield {"event": "error", "data": {"code": "LLM_ERROR", "message": str(e)}}
            yield {"event": "done", "data": {}}

    # ── Search Notes Agent Loop ───────────────────────────────────────────

    async def _execute_search_notes(
        self, messages: List[Dict], query: str, model: str, tokens_used: Optional[int]
    ) -> Dict[str, Any]:
        """Non-streaming agent loop for search_notes."""
        from core.rag_engine import get_rag_engine
        rag = get_rag_engine()
        db = SessionLocal()
        try:
            results = await rag.search(db, query, top_k=3)
        finally:
            db.close()

        if results:
            context = "用户的历史笔记搜索结果：\n" + "\n".join(
                f"- [{r['title']}] (更新于 {r['updated_at']}): {r['content']}"
                for r in results
            )
        else:
            context = "未在用户的历史笔记中找到相关内容。"

        # Send results back to LLM for summarization
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_search", "type": "function", "function": {"name": "search_notes", "arguments": json.dumps({"query": query})}}
        ]})
        messages.append({"role": "tool", "tool_call_id": "call_search", "content": context})

        try:
            response = await with_retry(
                lambda: litellm.acompletion(
                    model=self._resolve_model(),
                    messages=messages,
                    temperature=0.3,
                    max_tokens=8192,
                    timeout=30,
                    **self._api_kwargs(),
                )
            )
            choice = response.choices[0]
            return {
                "intent": "chat",
                "confidence": 0.9,
                "action": "search_notes",
                "params": {"query": query},
                "reply": choice.message.content or "已找到相关笔记。",
                "model": response.model,
                "tokens_used": (response.usage.total_tokens if response.usage else tokens_used),
            }
        except Exception:
            return {
                "intent": "chat",
                "confidence": 0.8,
                "action": "search_notes",
                "params": {"query": query},
                "reply": context,
                "model": model,
                "tokens_used": tokens_used,
            }

    async def _agent_search_notes(
        self, messages: List[Dict], query: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming agent loop for search_notes."""
        from core.rag_engine import get_rag_engine
        rag = get_rag_engine()
        db = SessionLocal()
        try:
            results = await rag.search(db, query, top_k=3)
        finally:
            db.close()

        if results:
            context = "用户的历史笔记搜索结果：\n" + "\n".join(
                f"- [{r['title']}] (更新于 {r['updated_at']}): {r['content']}"
                for r in results
            )
        else:
            context = "未在用户的历史笔记中找到相关内容。"

        # Send results back to LLM
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_search", "type": "function", "function": {"name": "search_notes", "arguments": json.dumps({"query": query})}}
        ]})
        messages.append({"role": "tool", "tool_call_id": "call_search", "content": context})

        try:
            stream = await with_retry(
                lambda: litellm.acompletion(
                    model=self._resolve_model(),
                    messages=messages,
                    temperature=0.3,
                    max_tokens=8192,
                    stream=True,
                    timeout=30,
                    **self._api_kwargs(),
                )
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield {"event": "message", "data": {"delta": delta.content}}
        except Exception as e:
            yield {"event": "message", "data": {"delta": f"\n[搜索完成，但 AI 总结暂不可用: {e}]"}}

        yield {"event": "done", "data": {}}

    def _merge_tool_calls(self, tool_calls: List[Any]) -> List[Dict]:
        by_index = {}
        for tc in tool_calls:
            idx = tc.index
            if idx not in by_index:
                by_index[idx] = {
                    "id": tc.id or "",
                    "type": tc.type or "function",
                    "function": {"name": "", "arguments": ""},
                }
            if tc.function:
                if tc.function.name:
                    by_index[idx]["function"]["name"] += tc.function.name
                if tc.function.arguments:
                    by_index[idx]["function"]["arguments"] += tc.function.arguments
        return list(by_index.values())


# Module-level singleton
_engine: Optional[IntentEngine] = None


def get_intent_engine() -> IntentEngine:
    """Return the shared IntentEngine singleton."""
    global _engine
    if _engine is None:
        _engine = IntentEngine()
    return _engine


def _is_retryable(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    status = getattr(error, 'status_code', None)
    if status is not None:
        return status in _RETRYABLE_STATUSES
    # Network-level errors (timeouts, connection issues) are retryable
    for exc_type in (asyncio.TimeoutError, ConnectionError, TimeoutError):
        if isinstance(error, exc_type):
            return True
    # litellm-specific retryable errors
    error_str = str(error).lower()
    for keyword in ('timeout', 'connection', 'rate limit', 'too many requests', 'internal server error', 'service unavailable'):
        if keyword in error_str:
            return True
    return False


async def with_retry(coro_factory, max_retries: int = 3, base_delay: float = 1.0):
    last_error = None
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1 and _is_retryable(e):
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            elif not _is_retryable(e) and attempt < max_retries - 1:
                # Non-retryable error — don't keep trying
                raise
    raise last_error

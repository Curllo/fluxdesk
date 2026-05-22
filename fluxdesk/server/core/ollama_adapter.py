import os
import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

import httpx

logger = logging.getLogger("fluxdesk")

DEFAULT_OLLAMA_MODEL = os.environ.get("FLUXDESK_OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.environ.get("FLUXDESK_OLLAMA_URL", "http://localhost:11434")


class OllamaAdapter:
    """Ollama local model adapter (second layer in the three-tier intent engine)."""

    def __init__(self, model: Optional[str] = None):
        self.model = model or DEFAULT_OLLAMA_MODEL
        self.base_url = OLLAMA_BASE_URL.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def is_available(self) -> bool:
        """Return True if Ollama is reachable on localhost."""
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Return a list of installed model names from Ollama."""
        try:
            resp = await self._client.get(f"{self.base_url}/api/tags", timeout=2.0)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            return [m.get("name") for m in models if m.get("name")]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []

    def _inject_tools_into_messages(
        self, messages: List[Dict], tools: List[Dict]
    ) -> List[Dict]:
        """Append tool descriptions to the system message for simulated function calling."""
        if not tools:
            return messages

        tool_desc = (
            "\n\nYou have access to the following tools:\n"
            + "\n".join(json.dumps(t, ensure_ascii=False) for t in tools)
            + "\n\nIf you want to call a tool, respond with a single JSON object containing "
            '"name" (the tool name) and "arguments" (a dict of parameters). '
            "Otherwise respond normally."
        )

        new_messages = []
        system_found = False
        for msg in messages:
            if msg.get("role") == "system":
                new_msg = {**msg, "content": (msg.get("content") or "") + tool_desc}
                new_messages.append(new_msg)
                system_found = True
            else:
                new_messages.append(msg)

        if not system_found:
            new_messages.insert(0, {"role": "system", "content": tool_desc})

        return new_messages

    def _try_parse_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """Detect a JSON object with 'name' and 'arguments' and return an OpenAI-style tool_call."""
        if not content or not content.strip():
            return None

        text = content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and "name" in obj and "arguments" in obj:
                return {
                    "id": "ollama_tool_call_0",
                    "type": "function",
                    "function": {
                        "name": obj["name"],
                        "arguments": json.dumps(obj["arguments"], ensure_ascii=False),
                    },
                }
        except json.JSONDecodeError:
            pass

        return None

    async def chat(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """Send a chat request to Ollama and parse the response."""
        tools = tools or []
        payload = {
            "model": self.model,
            "messages": self._inject_tools_into_messages(messages, tools),
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        resp = await self._client.post(f"{self.base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        assistant_msg = data.get("message", {})
        content = assistant_msg.get("content", "")

        tool_call = self._try_parse_tool_call(content)
        if tool_call:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call],
            }

        return {
            "role": "assistant",
            "content": content,
            "tool_calls": None,
        }

    async def stream_chat(
        self,
        messages: List[Dict],
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a chat request from Ollama, yielding delta chunks."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with self._client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = chunk.get("message", {})
                delta = msg.get("content", "")
                if delta:
                    yield {"delta": delta}


# Module-level singleton
_ollama_adapter: Optional[OllamaAdapter] = None


def get_ollama_adapter() -> OllamaAdapter:
    """Return the shared OllamaAdapter singleton."""
    global _ollama_adapter
    if _ollama_adapter is None:
        _ollama_adapter = OllamaAdapter()
    return _ollama_adapter

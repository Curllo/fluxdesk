import json
import os
import re
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from models.schemas import ChatMessage, ApiResponse
from utils.security import verify_api_token
from core.rule_engine import RuleEngine
from core.intent_engine import get_intent_engine

router = APIRouter()
rule_engine = RuleEngine()
intent_engine = get_intent_engine()

# Pattern to extract the actual user message from workspace-context-prefixed input
_USER_MSG_RE = re.compile(r'(?:^|\n)用户:\s*(.+?)\s*$', re.MULTILINE)


def _extract_user_message(full_text: str) -> str:
    """Strip workspace context prefix, keep just the user message."""
    m = _USER_MSG_RE.search(full_text)
    return m.group(1) if m else full_text


@router.post("/chat")
async def chat(
    req: ChatMessage,
    token: str = Depends(verify_api_token),
) -> ApiResponse:
    # First try rule engine (offline, 0ms latency)
    user_msg = _extract_user_message(req.message)
    result = rule_engine.match(user_msg)
    if result:
        return ApiResponse(data=result)

    # Fallback to LLM via LiteLLM
    response = await intent_engine.parse(user_msg, req.history)
    return ApiResponse(data=response)


@router.post("/chat/stream")
async def chat_stream(
    req: ChatMessage,
    token: str = Depends(verify_api_token),
):
    async def event_generator():
        # Try rule engine first
        user_msg = _extract_user_message(req.message)
        result = rule_engine.match(user_msg)
        if result:
            yield sse_event("message", {"delta": result.get("reply", "好的，已为您处理。")})
            action = result.get("action", "")
            if action and action != "reply":
                yield sse_event("tool_call", {
                    "name": action,
                    "arguments": json.dumps(result.get("params", {})),
                })
                yield sse_event("tool_result", {"result": "done", "success": True, "params": result.get("params", {})})
            yield sse_event("done", {})
            return

        # Streaming LLM response via LiteLLM
        async for event in intent_engine.stream_parse(user_msg, req.history):
            yield sse_event(event["event"], event["data"])

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

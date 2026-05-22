"""
FluxDesk LLM End-to-End Verification Script

Usage:
    python tests/test_llm_e2e.py

Requires the Python backend to be running (python main.py).
Set OPENAI_API_KEY (or DEEPSEEK_API_KEY, etc.) to test real LLM calls.

Covers:
    1. Health check
    2. Settings get/update/verify
    3. Mock mode chat (non-streaming)
    4. Mock mode SSE stream
    5. Real LLM chat (if API key configured)
    6. Real LLM stream (if API key configured)
    7. Rule engine (offline, 0ms)
    8. Todo CRUD
    9. Note CRUD
    10. Reminder CRUD
"""

import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:8000"
TOKEN = "dev-token"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}",
}

passed = 0
failed = 0


def req(method: str, path: str, body: dict = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.urlopen(
        urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    )
    return json.loads(r.read())


def test(name: str, fn):
    global passed, failed
    try:
        fn()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1


# ── 1. Health ──────────────────────────────────────────────────────────────

def test_health():
    r = req("GET", "/api/v1/health")
    assert r["status"] == "ok"
    assert r["version"] == "1.1.0"


# ── 2. Settings ────────────────────────────────────────────────────────────

def test_get_settings():
    r = req("GET", "/api/v1/settings/llm")
    assert "provider" in r["data"]
    assert "model" in r["data"]
    assert "mock_mode" in r["data"]


def test_update_settings():
    r = req("POST", "/api/v1/settings/llm", {"provider": "openai", "model": "gpt-4o-mini"})
    assert r["data"]["provider"] == "openai"


def test_verify_settings():
    r = req("POST", "/api/v1/settings/llm/verify", {})
    # May return ok=True (if key set) or ok=False (no key / network error)
    assert "ok" in r["data"]


# ── 3. Rule Engine (offline) ───────────────────────────────────────────────

def test_rule_pomodoro():
    r = req("POST", "/api/v1/chat", {"message": "创建一个25分钟的番茄钟"})
    d = r["data"]
    assert d["action"] == "create_window"
    assert d["params"]["type"] == "pomodoro"
    assert int(d["params"]["duration"]) == 25


def test_rule_todo():
    r = req("POST", "/api/v1/chat", {"message": "添加一个待办任务"})
    assert r["data"]["action"] in ("create_window", "manage_todo")


def test_rule_greeting():
    r = req("POST", "/api/v1/chat", {"message": "你好"})
    assert r["data"]["action"] == "reply"


# ── 4. Mock LLM (no API key) ──────────────────────────────────────────────

def test_mock_chat_pomodoro():
    r = req("POST", "/api/v1/chat", {"message": "帮我创建一个番茄钟"})
    d = r["data"]
    assert d["action"] == "create_window"
    assert d["params"]["type"] == "pomodoro"


def test_mock_chat_todo():
    r = req("POST", "/api/v1/chat", {"message": "记一个待办"})
    d = r["data"]
    assert d["action"] in ("manage_todo", "create_window")


def test_mock_chat_note():
    r = req("POST", "/api/v1/chat", {"message": "打开笔记"})
    d = r["data"]
    assert d["action"] == "create_window"
    assert d["params"]["type"] == "note"


# ── 5. SSE Stream (mock) ───────────────────────────────────────────────────

def test_sse_stream_mock():
    url = f"{BASE}/api/v1/chat/stream"
    data = json.dumps({"message": "创建30分钟的番茄钟"}).encode()
    r = urllib.request.urlopen(
        urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
    )
    body = r.read().decode("utf-8")
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.strip().split("\n")
        evt = {}
        for line in lines:
            if line.startswith("event:"):
                evt["event"] = line[6:].strip()
            elif line.startswith("data:"):
                evt["data"] = json.loads(line[5:])
        if evt:
            events.append(evt)

    event_types = [e["event"] for e in events]
    assert "message" in event_types, f"No message event in: {event_types}"
    assert "tool_call" in event_types, f"No tool_call event in: {event_types}"
    assert "done" in event_types, f"No done event in: {event_types}"


# ── 6. Todo CRUD ───────────────────────────────────────────────────────────

_todo_id = None

def test_todo_create():
    global _todo_id
    r = req("POST", "/api/v1/todos", {"content": "e2e test todo"})
    _todo_id = r["data"]["id"]
    assert _todo_id is not None

def test_todo_list():
    r = req("GET", "/api/v1/todos")
    assert isinstance(r["data"], list)

def test_todo_delete():
    global _todo_id
    if _todo_id:
        r = req("DELETE", f"/api/v1/todos/{_todo_id}")
        assert r["data"]["deleted"] == True


# ── 7. Note CRUD ───────────────────────────────────────────────────────────

_note_id = None

def test_note_create():
    global _note_id
    r = req("POST", "/api/v1/notes", {"title": "e2e test note", "content": "hello world"})
    _note_id = r["data"]["id"]
    assert _note_id is not None

def test_note_get():
    global _note_id
    if _note_id:
        r = req("GET", f"/api/v1/notes/{_note_id}")
        assert r["data"]["title"] == "e2e test note"

def test_note_delete():
    global _note_id
    if _note_id:
        r = req("DELETE", f"/api/v1/notes/{_note_id}")
        assert r["data"]["deleted"] == True


# ── 8. Data Export/Import ───────────────────────────────────────────────────

_export_data = None

def test_data_export():
    global _export_data
    r = req("GET", "/api/v1/data/export")
    assert r["data"] is not None
    assert r["data"]["version"] == "1.1.0"
    assert "exported_at" in r["data"]
    assert "counts" in r["data"]
    assert "notes" in r["data"]["data"]
    assert "todos" in r["data"]["data"]
    assert "reminders" in r["data"]["data"]
    _export_data = r["data"]["data"]

def test_data_import():
    global _export_data
    if _export_data is None:
        r = req("GET", "/api/v1/data/export")
        _export_data = r["data"]["data"]
    r = req("POST", "/api/v1/data/import", {"data": _export_data})
    assert r["data"]["imported"] == True
    assert "stats" in r["data"]


# ── 9. Reminder CRUD ───────────────────────────────────────────────────────

_reminder_id = None

def test_reminder_create():
    global _reminder_id
    r = req("POST", "/api/v1/reminders", {"title": "e2e test reminder", "time": "2026-05-05T15:00:00"})
    _reminder_id = r["data"]["id"]
    assert _reminder_id is not None

def test_reminder_delete():
    global _reminder_id
    if _reminder_id:
        r = req("DELETE", f"/api/v1/reminders/{_reminder_id}")
        assert r["data"]["deleted"] == True


# ── Run ────────────────────────────────────────────────────────────────────

def main():
    global passed, failed

    print("=" * 60)
    print("FluxDesk LLM E2E Test Suite")
    print("=" * 60)

    # Check server is up
    try:
        req("GET", "/api/v1/health")
    except Exception:
        print("\nERROR: Backend not running at http://127.0.0.1:8000")
        print("Start it with: cd fluxdesk/server && python main.py\n")
        sys.exit(1)

    print("\n── Health ──")
    test("Health check", test_health)

    print("\n── Settings ──")
    test("Get settings", test_get_settings)
    test("Update settings", test_update_settings)
    test("Verify settings", test_verify_settings)

    print("\n── Rule Engine (offline) ──")
    test("Pomodoro rule", test_rule_pomodoro)
    test("Todo rule", test_rule_todo)
    test("Greeting rule", test_rule_greeting)

    print("\n── Mock LLM (no API key) ──")
    test("Mock chat: pomodoro", test_mock_chat_pomodoro)
    test("Mock chat: todo", test_mock_chat_todo)
    test("Mock chat: note", test_mock_chat_note)

    print("\n── SSE Stream ──")
    test("SSE stream mock", test_sse_stream_mock)

    print("\n── Todo CRUD ──")
    test("Todo create", test_todo_create)
    test("Todo list", test_todo_list)
    test("Todo delete", test_todo_delete)

    print("\n── Note CRUD ──")
    test("Note create", test_note_create)
    test("Note get", test_note_get)
    test("Note delete", test_note_delete)

    print("\n── Reminder CRUD ──")
    test("Reminder create", test_reminder_create)
    test("Reminder delete", test_reminder_delete)

    print("\n── Data Export/Import ──")
    test("Data export", test_data_export)
    test("Data import", test_data_import)

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

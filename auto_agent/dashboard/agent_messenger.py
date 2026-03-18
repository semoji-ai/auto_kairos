# -*- coding: utf-8 -*-
"""
Agent Messenger — 에이전트 간 메시지를 실시간 SSE로 전송.

사용법 (백엔드):
    from auto_agent.dashboard.agent_messenger import messenger, post_message
    post_message("Director", "리서치 시작", project_slug="코카콜라의_역사")

사용법 (프론트):
    const es = new EventSource('/api/agent-messages/stream');
    es.onmessage = (e) => { const msg = JSON.parse(e.data); ... };
"""
import asyncio
import json
import time
from collections import deque
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

router = APIRouter(prefix="/api/agent-messages", tags=["agent-messenger"])

# ── 메시지 큐 (파일 영속 + 인메모리 캐시) ──

MAX_HISTORY = 1000
_PERSIST_FILE = None

def _get_persist_path():
    global _PERSIST_FILE
    if _PERSIST_FILE is None:
        from auto_agent.paths import get_workspace_dir
        p = get_workspace_dir() / ".auto_agent" / "agent_messages.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        _PERSIST_FILE = p
    return _PERSIST_FILE

def _load_persisted() -> deque:
    """시작 시 파일에서 메시지 로드."""
    msgs = deque(maxlen=MAX_HISTORY)
    path = _get_persist_path()
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    msgs.append(json.loads(line))
        except Exception:
            pass
    return msgs

_messages: deque = deque(maxlen=MAX_HISTORY)
_subscribers: list[asyncio.Queue] = []
_msg_id = 0
_initialized = False


def post_message(
    agent: str,
    text: str,
    phase: str = "",
    project_slug: str = "",
    level: str = "info",
    data: dict = None,
):
    """에이전트 메시지를 큐에 추가하고 모든 SSE 구독자에게 전달."""
    global _msg_id, _messages, _initialized
    if not _initialized:
        _messages = _load_persisted()
        _msg_id = max((m.get("id", 0) for m in _messages), default=0)
        _initialized = True

    _msg_id += 1

    msg = {
        "id": _msg_id,
        "agent": agent,
        "text": text,
        "phase": phase,
        "project": project_slug,
        "level": level,  # info, success, warning, error
        "data": data or {},
        "timestamp": time.time(),
    }
    _messages.append(msg)

    # 파일에 영속 저장 (append)
    try:
        with open(_get_persist_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # 모든 SSE 구독자에게 전달
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)


# ── SSE 엔드포인트 ──

async def _sse_generator(request: Request, queue: asyncio.Queue, project: str = ""):
    """SSE 이벤트 생성기. project가 지정되면 해당 프로젝트 메시지만 전달."""
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=15)
                if project and msg.get("project", "") != project:
                    continue
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            except asyncio.TimeoutError:
                # 15초마다 keepalive
                yield f": keepalive\n\n"
    finally:
        if queue in _subscribers:
            _subscribers.remove(queue)


@router.get("/stream")
async def message_stream(request: Request, project: str = ""):
    """SSE 스트림 — 에이전트 메시지 실시간 수신. project 파라미터로 필터링."""
    queue = asyncio.Queue(maxsize=100)
    _subscribers.append(queue)

    return StreamingResponse(
        _sse_generator(request, queue, project=project),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def message_history(limit: int = 50, project: str = ""):
    """최근 메시지 히스토리. project 파라미터로 필터링."""
    global _messages, _initialized
    if not _initialized:
        _messages = _load_persisted()
        _initialized = True
    if project:
        filtered = [m for m in _messages if m.get("project", "") == project]
        msgs = filtered[-limit:]
    else:
        msgs = list(_messages)[-limit:]
    return {"messages": msgs}


@router.post("/send")
async def send_message(request: Request):
    """외부에서 메시지 전송 (HTTP POST)."""
    body = await request.json()
    post_message(
        agent=body.get("agent", "System"),
        text=body.get("text", ""),
        phase=body.get("phase", ""),
        project_slug=body.get("project", ""),
        level=body.get("level", "info"),
        data=body.get("data"),
    )
    return {"ok": True}

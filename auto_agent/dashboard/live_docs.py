"""Live document snapshot helpers for dashboard tabs."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


LIVE_DOC_TYPES = {"research", "outline", "manuscript", "storyboard"}


def reduce_doc_events(events: List[dict], doc_type: str) -> Optional[dict]:
    if doc_type not in LIVE_DOC_TYPES:
        return None

    state: Dict[str, Any] = {
        "doc_type": doc_type,
        "status": "idle",
        "doc_id": None,
        "content": {},
        "updated_at": None,
    }

    seen = False
    for event in events:
        if event.get("kind", "message") != "doc_update":
            continue
        data = event.get("data", {}) or {}
        if data.get("doc_type") != doc_type:
            continue
        seen = True
        state["doc_id"] = data.get("doc_id") or state["doc_id"]
        state["updated_at"] = event.get("timestamp") or state["updated_at"]

        op = data.get("op")
        value = data.get("value")
        path = data.get("path") or "payload"
        meta = data.get("meta") or {}

        if op == "snapshot":
            state["content"] = value or {}
        elif op == "append_text":
            state.setdefault("content", {}).setdefault("raw_text", "")
            state["content"]["raw_text"] += value or ""
        elif op == "upsert":
            state.setdefault("content", {})[path] = value
        elif op == "status" and meta.get("status"):
            state["status"] = meta["status"]

        if meta.get("status"):
            state["status"] = meta["status"]

    return state if seen else None


def load_live_doc_snapshot(project_slug: str, doc_type: str, limit: int = 500) -> Optional[dict]:
    from auto_agent.dashboard import agent_messenger

    history = agent_messenger.message_history_sync(limit=limit, project=project_slug)
    messages = history.get("messages", []) if history else []
    return reduce_doc_events(messages, doc_type=doc_type)
